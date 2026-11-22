#!/usr/bin/env bash
# Remet la base de la boutique dans l'état d'une sauvegarde.
#   sudo ./restaurer.sh               la liste des sauvegardes, la plus récente en haut
#   sudo ./restaurer.sh FICHIER       restaure ce fichier (.sql.gz, son nom seul suffit), après confirmation
#
# Choisis la sauvegarde d'AVANT l'incident : juste après une panne, la plus récente est souvent
# celle d'une base vide (la sauvegarde, elle, a continué de tourner).
set -euo pipefail
cd "$(dirname "$0")"

erreur() {
	echo "restaurer.sh : $*" >&2
	exit 1
}
[ "$(id -u)" -eq 0 ] || erreur "lance-le avec sudo : sudo $0 $*"
[ -f .env ] || erreur "il manque .env : lance-le dans le dossier du projet"
dossier=$(sed -n 's/^DOSSIER_SAUVEGARDES=//p' .env | tail -n 1)
dossier=${dossier:-/var/backups/mboa-market}

if [ "$#" -eq 0 ]; then
	echo "Les sauvegardes de $dossier, la plus récente en haut (l'heure est dans le nom) :"
	find "$dossier" -maxdepth 1 -name '*.sql.gz' -printf '  %f\n' 2> /dev/null | sort -r | head -n 15
	echo "Pour en restaurer une : sudo $0 <fichier>"
	exit 0
fi

fichier=$1
[ -f "$fichier" ] || [ ! -f "$dossier/$fichier" ] || fichier="$dossier/$fichier"   # le nom seul suffit
[ -f "$fichier" ] || erreur "introuvable : $fichier"
gzip -t "$fichier" 2> /dev/null || erreur "ce fichier est abîmé (gzip -t le refuse) : $fichier"

if [ -t 0 ]; then
	read -r -p "La base va être remplacée par $(basename "$fichier"). Tape « oui » pour continuer : " reponse
	[ "$reponse" = oui ] || {
		echo "Rien n'est changé."
		exit 1
	}
fi

# Pas de sauvegarde pendant qu'on restaure ; elle repart à la fin, même si la restauration échoue.
docker compose --progress quiet stop sauvegarde
trap 'docker compose --progress quiet start sauvegarde' EXIT

gunzip -c "$fichier" | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /dev/null
docker compose exec -T redis redis-cli DEL produits > /dev/null    # le cache garde l'ancienne liste : on le vide
echo "Restauré : $(basename "$fichier")"
echo "Vérifie : curl -s http://127.0.0.1:8083/api/produits"
