#!/usr/bin/env bash
# Une sauvegarde de la base : compressée, datée et vérifiée. crond la lance chaque minute (voir crontab).
# pg_dump lit tout seul PGHOST, PGDATABASE, PGUSER et PGPASSWORD : compose.yaml les donne au conteneur.
set -euo pipefail                            # bash est dans l'image postgres:18-alpine

dossier=/sauvegardes
garder=${GARDER_MINUTES:-60}                 # au-delà de cet âge (en minutes), une sauvegarde est effacée
fichier="$dossier/$PGDATABASE-$(date +%Y%m%d-%H%M).sql.gz"
umask 077                                    # root seul lit une sauvegarde : elle contient TOUTES les données

# 1. Dans un fichier .part : un .sql.gz n'existe que s'il est complet.
#    --clean --if-exists : à la restauration, la table est remplacée, pas doublée.
if ! pg_dump --clean --if-exists | gzip > "$fichier.part"; then
	echo "$(date '+%F %T') ÉCHEC de la sauvegarde : le message de pg_dump est juste au-dessus" >&2
	rm -f "$fichier.part"
	exit 1
fi
gzip -t "$fichier.part"                      # 2. Le fichier se relit ?
mv "$fichier.part" "$fichier"                # 3. Alors seulement, il prend son vrai nom.

# 4. La rotation : on garde la dernière heure, le reste est effacé.
find "$dossier" -name "$PGDATABASE-*.sql.gz" -mmin +"$garder" -delete
echo "$(date '+%F %T') sauvegarde $(basename "$fichier") : $(du -h "$fichier" | cut -f1), $(find "$dossier" -name "$PGDATABASE-*.sql.gz" | wc -l) au total"
