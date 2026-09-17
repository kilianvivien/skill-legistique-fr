# legistique-fr : installation

Skill pour agents IA : rédaction et correction de textes normatifs français (loi, ordonnance, décret,
arrêté, article de code) selon le Guide de légistique du Conseil d'Etat et du SGG.

La skill suit le standard ouvert Agent Skills (https://agentskills.io) : elle fonctionne avec Claude,
Codex, Mistral Vibe, Cursor, Gemini CLI, GitHub Copilot et tout agent compatible.

Cette archive contient :

```
README.md            ← ce fichier
legistique-fr/       ← la skill (c'est ce dossier qu'il faut installer)
├── SKILL.md
└── references/      ← fiches de synthèse
    └── guide/       ← texte intégral du Guide de légistique (101 fiches + index)
```

Le dossier `references/guide/` reproduit le Guide de légistique publié sur Légifrance (licence
etalab-2.0), converti automatiquement : seule la version publiée sur Légifrance fait foi.

## Principe

Installer la skill, c'est copier le dossier `legistique-fr/` dans le dossier de skills de votre agent.
Le résultat attendu : `<dossier de skills>/legistique-fr/SKILL.md`.

| Agent | Pour tous vos projets | Pour un seul projet |
|---|---|---|
| Codex (OpenAI) | `~/.agents/skills/` | `.agents/skills/` |
| Mistral Vibe | `~/.vibe/skills/` ou `~/.agents/skills/` | `.vibe/skills/` ou `.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Cursor | `~/.cursor/skills/` ou `~/.agents/skills/` | `.cursor/skills/` ou `.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` ou `~/.agents/skills/` | `.gemini/skills/` ou `.agents/skills/` |
| GitHub Copilot | `~/.copilot/skills/` ou `~/.agents/skills/` | `.github/skills/` ou `.agents/skills/` |

`~/.agents/skills/` est le dossier commun : une seule installation y sert à Codex, Mistral Vibe,
Cursor, Gemini CLI et GitHub Copilot.

## Codex (OpenAI)

```bash
mkdir -p ~/.agents/skills
```

```bash
unzip legistique-fr.zip 'legistique-fr/*' -d ~/.agents/skills/
```

Redémarrez Codex. Appel explicite : `$legistique-fr` dans un message, ou `/skills` pour la liste.

## Mistral Vibe

```bash
mkdir -p ~/.vibe/skills
```

```bash
unzip legistique-fr.zip 'legistique-fr/*' -d ~/.vibe/skills/
```

Relancez `vibe`. Les skills d'un projet (`.vibe/skills/` ou `.agents/skills/`) ne sont chargées que
si le dossier du projet est un dossier de confiance.

## Claude Code

```bash
mkdir -p ~/.claude/skills
```

```bash
unzip legistique-fr.zip 'legistique-fr/*' -d ~/.claude/skills/
```

Redémarrez Claude Code. Appel explicite : `/legistique-fr`.

## Claude.ai et application Claude (bureau, web)

1. Ouvrir **Paramètres → Capacités** et vérifier que l'exécution de code est activée.
2. Dans la rubrique **Skills**, choisir **Importer une skill** et sélectionner l'archive
   `legistique-fr.zip`.
3. Activer la skill `legistique-fr` dans la liste.

Si l'import refuse l'archive, décompressez-la, puis compressez **uniquement le dossier
`legistique-fr/`** et importez ce nouveau fichier.

## Autres agents

Décompressez le dossier `legistique-fr/` dans le dossier de skills indiqué par la documentation de
votre agent (liste des agents compatibles : https://agentskills.io/clients). Dans le doute,
`~/.agents/skills/` est reconnu par la plupart d'entre eux.

## Utilisation

La skill se déclenche d'elle-même dès qu'on demande de rédiger, relire ou corriger un texte
normatif. Exemples :

- « Fais un projet de décret à partir de cette note : … »
- « Relis ce projet d'arrêté et dis-moi ce qui ne va pas : … »
- « Comment rédiger l'abrogation d'un alinéa dans un code ? »

Documentation complète et exemples : https://github.com/kilianvivien/skill-legistique-fr
