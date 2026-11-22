"""L'API de Mboa Market, version 3 : les produits dans PostgreSQL, un cache et un compteur dans Redis.

Derrière Traefik, tout est sous /api (Traefik enlève /api avant de passer la requête) :
  GET  /api/          qui répond : le service, sa version, le conteneur
  GET  /api/sante     l'état de l'API (pour le healthcheck) : la base et le cache répondent-ils ?
  GET  /api/produits  la liste des produits, gardée 30 secondes dans Redis (l'en-tête X-Cache dit HIT ou MISS)
  POST /api/produits  ajoute un produit : {"nom": "Savon noir", "prix": 600} ; le cache est vidé
  POST /api/visites   compte une visite de la boutique, et rend le total

Les réglages viennent de l'environnement (compose.yaml, qui les prend dans .env) :
  MBOA_DB_HOST                  le nom du service de la base (par défaut « db »)
  POSTGRES_DB, POSTGRES_USER    la base et l'utilisateur (par défaut boutique et mboa)
  POSTGRES_PASSWORD             le mot de passe de la base
  MBOA_REDIS_HOST               le nom du service Redis (par défaut « redis »)
  REDIS_PASSWORD                le mot de passe de Redis
"""
import json
import os
import socket

import psycopg
import redis
from flask import Flask, jsonify, request
from redis.backoff import NoBackoff
from redis.retry import Retry

VERSION = "3.0"
HOTE_DB = os.environ.get("MBOA_DB_HOST", "db")
HOTE_REDIS = os.environ.get("MBOA_REDIS_HOST", "redis")
CLE_PRODUITS = "produits"  # la clé Redis qui garde la liste
DUREE_CACHE = 30  # secondes : au-delà, Redis l'oublie tout seul

TABLE = """
CREATE TABLE IF NOT EXISTS produits (
    id      SERIAL PRIMARY KEY,
    nom     TEXT NOT NULL,
    prix    INTEGER NOT NULL CHECK (prix >= 0),
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

app = Flask(__name__)
app.json.ensure_ascii = False  # « Riz parfumé », pas « Riz parfumé »
app.json.sort_keys = False  # les champs dans l'ordre où on les écrit

# Le client Redis ne se connecte qu'au premier appel : l'API démarre même si Redis est en retard.
# Aucun nouvel essai, une seconde au plus : si Redis tombe, la boutique continue sans cache, tout de suite.
cache = redis.Redis(
    host=HOTE_REDIS,
    port=6379,
    password=os.environ.get("REDIS_PASSWORD") or None,
    socket_connect_timeout=1,
    socket_timeout=1,
    retry=Retry(NoBackoff(), 0),
    decode_responses=True,
)


def connexion():
    return psycopg.connect(
        host=HOTE_DB,
        port=int(os.environ.get("MBOA_DB_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "boutique"),
        user=os.environ.get("POSTGRES_USER", "mboa"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        connect_timeout=3,
        autocommit=True,
    )


def base():
    """Une connexion, et la table produits : créée si elle manque, par un seul worker à la fois."""
    conn = connexion()
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(4242)")
        conn.execute(TABLE)
    return conn


def en_texte(produit):
    i, nom, prix, cree_le = produit
    return {"id": i, "nom": nom, "prix": prix, "cree_le": cree_le.isoformat(timespec="seconds")}


def json_brut(texte, code=200, **entetes):
    reponse = app.response_class(texte, status=code, mimetype="application/json")
    reponse.headers.update(entetes)
    return reponse


@app.errorhandler(psycopg.Error)
def base_injoignable(probleme):
    return jsonify(erreur="la base ne répond pas", raison=str(probleme).strip()), 503


@app.after_request
def qui_a_servi(reponse):
    # Le nom du conteneur qui a répondu : avec trois API derrière Traefik, on le voit changer.
    reponse.headers["X-Servi-Par"] = socket.gethostname()
    return reponse


@app.get("/")
def accueil():
    return jsonify(service="mboa-api", version=VERSION, conteneur=socket.gethostname(), base=HOTE_DB, cache=HOTE_REDIS)


@app.get("/sante")
def sante():
    """ok : tout répond. degrade : Redis ne répond pas, mais la boutique marche (sans cache). ko : pas de base."""
    etat = {"etat": "ok", "base": "ok", "cache": "ok"}
    try:
        with connexion() as conn:
            conn.execute("SELECT 1")
    except (psycopg.Error, OSError) as probleme:
        etat.update(etat="ko", base="ko", raison=str(probleme).strip())
    try:
        cache.ping()
    except redis.RedisError as probleme:
        etat["cache"] = "ko"
        if etat["etat"] == "ok":
            etat.update(etat="degrade", raison=f"Redis : {probleme}")
    return jsonify(etat), 503 if etat["etat"] == "ko" else 200


@app.get("/produits")
def lister():
    try:
        deja_la = cache.get(CLE_PRODUITS)
    except redis.RedisError as probleme:
        app.logger.warning("Redis ne répond pas (%s) : la liste vient de la base", probleme)
        deja_la = None
    if deja_la is not None:
        return json_brut(deja_la, **{"X-Cache": "HIT"})  # la base n'a même pas été appelée
    with base() as conn:
        lignes = conn.execute("SELECT id, nom, prix, cree_le FROM produits ORDER BY id").fetchall()
    texte = json.dumps([en_texte(ligne) for ligne in lignes], ensure_ascii=False)
    try:
        cache.set(CLE_PRODUITS, texte, ex=DUREE_CACHE)
    except redis.RedisError:
        pass  # sans cache, on sert quand même
    return json_brut(texte, **{"X-Cache": "MISS"})


@app.post("/produits")
def ajouter():
    produit = request.get_json(silent=True) or {}
    nom, prix = produit.get("nom"), produit.get("prix")
    nom_ok = isinstance(nom, str) and 0 < len(nom.strip()) <= 80
    prix_ok = isinstance(prix, int) and not isinstance(prix, bool) and 0 <= prix <= 10_000_000
    if not (nom_ok and prix_ok):
        return jsonify(erreur='il faut {"nom": "…" (80 caractères au plus), "prix": un entier positif}'), 400
    with base() as conn:
        ligne = conn.execute(
            "INSERT INTO produits (nom, prix) VALUES (%s, %s) RETURNING id, nom, prix, cree_le", (nom.strip(), prix)
        ).fetchone()
    try:
        cache.delete(CLE_PRODUITS)  # la liste a changé : la prochaine lecture ira à la base
    except redis.RedisError as probleme:
        app.logger.warning("Redis ne répond pas (%s) : le cache se videra seul dans %s s", probleme, DUREE_CACHE)
    return jsonify(en_texte(ligne)), 201


@app.post("/visites")
def visiter():
    try:
        total = cache.incr("visites")
    except redis.RedisError:
        return jsonify(erreur="le compteur (Redis) ne répond pas"), 503
    return jsonify(visites=total)
