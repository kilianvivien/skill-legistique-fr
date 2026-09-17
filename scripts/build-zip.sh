#!/usr/bin/env bash
# Construit legistique-fr.zip à la racine du dépôt : skill + README d'installation.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/legistique-fr.zip"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cp -R "$root/legistique-fr" "$tmp/legistique-fr"
rm -rf "$tmp/legistique-fr/evals"
cp "$root/distribution/README.md" "$tmp/README.md"

rm -f "$out"
(cd "$tmp" && zip -rqX "$out" README.md legistique-fr -x '*.DS_Store')
unzip -tq "$out"
echo "Archive : $out"
