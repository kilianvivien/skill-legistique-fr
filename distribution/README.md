# legistique-fr : installation

Skill pour Claude : rédaction et correction de textes normatifs français (loi, ordonnance, décret,
arrêté, article de code) selon le Guide de légistique du Conseil d'Etat et du SGG.

Cette archive contient :

```
README.md            ← ce fichier
legistique-fr/       ← la skill (c'est ce dossier qu'il faut installer)
├── SKILL.md
└── references/
```

## Claude.ai et application Claude (bureau, web)

1. Ouvrir **Paramètres → Capacités** et vérifier que l'exécution de code est activée.
2. Dans la rubrique **Skills**, choisir **Importer une skill** et sélectionner l'archive
   `legistique-fr.zip`.
3. Activer la skill `legistique-fr` dans la liste.

Si l'import refuse l'archive, décompressez-la, puis compressez **uniquement le dossier
`legistique-fr/`** et importez ce nouveau fichier.

## Claude Code

Pour tous vos projets :

```bash
unzip legistique-fr.zip 'legistique-fr/*' -d ~/.claude/skills/
```

Pour un seul projet (à lancer à la racine du projet) :

```bash
unzip legistique-fr.zip 'legistique-fr/*' -d .claude/skills/
```

Vérification : le fichier `~/.claude/skills/legistique-fr/SKILL.md` (ou
`.claude/skills/legistique-fr/SKILL.md`) doit exister. Redémarrez Claude Code.

## Utilisation

La skill se déclenche d'elle-même dès qu'on demande de rédiger, relire ou corriger un texte
normatif. Exemples :

- « Fais un projet de décret à partir de cette note : … »
- « Relis ce projet d'arrêté et dis-moi ce qui ne va pas : … »
- « Comment rédiger l'abrogation d'un alinéa dans un code ? »

Dans Claude Code, on peut aussi l'appeler explicitement avec `/legistique-fr`.

Documentation complète et exemples : https://github.com/kilianvivien/skill-legistique-fr
