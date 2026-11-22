# À FAIRE (étape 6, P2-06) : l'image de la sauvegarde.
#   FROM postgres:18-alpine : la même image que la base (pg_dump doit avoir la même version que le serveur)
#   sauvegarder.sh devient /usr/local/bin/sauvegarder, exécutable : COPY --chmod=755
#   crontab (à côté) devient /etc/crontabs/root
#   un HEALTHCHECK : la dernière sauvegarde a moins de 2 minutes
#       find /sauvegardes -name '*.sql.gz' -mmin -2 | grep -q .
#   crond au premier plan, son journal sur la sortie d'erreur : ENTRYPOINT ["crond", "-f", "-d", "8"]


FROM postgres:18-alpine
COPY --chmod=755 sauvegarder.sh /usr/local/bin/sauvegarder
COPY crontab /etc/crontabs/root
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD find /sauvegardes -name '*.sql.gz' -mmin -2 | grep -q . || exit 1
ENTRYPOINT ["crond", "-f", "-d", "8"]
