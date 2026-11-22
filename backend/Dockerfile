# À FAIRE (étape 3, P2-03) : l'image de l'API, en deux étages, comme au TP 7 et au TP 8.
#   Étage 1 : FROM python:3.12 AS construction ; un venv dans /opt/venv ; pip install -r requirements.txt
#   Étage 2 : FROM python:3.12-slim ; un compte mboa (uid 10001) ; le venv copié de l'étage 1 ; app.py ;
#             USER mboa ; EXPOSE 8000 ; un HEALTHCHECK toutes les 10 s sur http://127.0.0.1:8000/sante ;
#             CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--no-control-socket", "app:app"]
# Ton modèle : ~/tp08/boutique/api/Dockerfile. Le support donne le fichier complet.
