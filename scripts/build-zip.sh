#!/usr/bin/env bash
# Construit, à la racine du dépôt :
# - legistique-fr.zip : skill + README d'installation ;
# - legistique-fr.skill : dossier de la skill seul, à importer tel quel.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/legistique-fr.zip"
skill="$root/legistique-fr.skill"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cp -R "$root/legistique-fr" "$tmp/legistique-fr"
rm -rf "$tmp/legistique-fr/evals"
cp "$root/distribution/README.md" "$tmp/README.md"

exclus=(-x '*.DS_Store' -x '*__pycache__*' -x '*.pyc')
rm -f "$out" "$skill"
(cd "$tmp" && zip -rqX "$out" README.md legistique-fr "${exclus[@]}")
(cd "$tmp" && zip -rqX "$skill" legistique-fr "${exclus[@]}")
unzip -tq "$out"
unzip -tq "$skill"
echo "Archive : $out"
echo "Skill : $skill"
