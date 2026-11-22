# L'image de l'API, version 2 : le Dockerfile multi-étapes du cours 5 (diapo 20), sans le dossier
# /donnees : les données sont maintenant dans PostgreSQL, un autre conteneur.

# Étape 1 : la construction. L'image complète, avec ses compilateurs. Elle ne part pas en production.
FROM python:3.12 AS construction
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Étape 2 : l'image de production. Python seul, l'environnement construit, le code, un utilisateur.
FROM python:3.12-slim
RUN groupadd --system --gid 10001 mboa \
    && useradd --system --uid 10001 --gid mboa --no-create-home --shell /usr/sbin/nologin mboa
COPY --from=construction /opt/venv /opt/venv
WORKDIR /app
COPY app.py .
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1
USER mboa
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/sante', timeout=2)"]
# --no-control-socket : gunicorn ne crée pas sa prise de contrôle (le compte mboa n'a pas de dossier personnel).
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--no-control-socket", "app:app"]
