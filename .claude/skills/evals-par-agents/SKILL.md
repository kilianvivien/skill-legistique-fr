---
name: evals-par-agents
description: >-
  Lance une campagne d'évaluation de la skill legistique-fr en comparant plusieurs versions
  (par exemple la dernière étiquette et l'arbre de travail) : exécution des cas par des sous-agents
  Claude Code (Sonnet par défaut), notation par un modèle indépendant via Codex (GPT 6.1 Sol par
  défaut), rapport comparatif. À utiliser quand on demande de « lancer les evals », « mesurer l'effet
  d'une modification », « comparer avec la version précédente », surtout si `claude -p` ou l'API
  Anthropic ne sont pas disponibles.
---

# Evals par agents

Cette procédure remplace `scripts/run_evals.py` quand on travaille depuis Claude Code : l'exécution
passe par des sous-agents (pas de `claude -p`, pas de clé API), la notation par la CLI Codex, ce qui
donne un juge indépendant du modèle évalué.

## 1. Choisir les cas et les versions

- Cas : identifiants de `legistique-fr/evals/evals.json`. Pour corroborer une modification, prendre
  les cas qui la ciblent et quelques cas d'autres fonctions (rédaction, relecture, analyse,
  amendement) pour détecter un recul.
- Versions : `courante` (arbre de travail, modifications non commitées comprises) et la référence de
  comparaison, en général la dernière étiquette (`git tag` ; par exemple `v0.5.3`).

## 2. Préparer la campagne

```
python3 scripts/evals_agents.py preparer --ids 1,2,11,12,16 --versions v0.5.3,courante
```

Le script affiche le dossier de campagne (`legistique-fr-workspace/evals-agents/<horodatage>/`) et
écrit `consignes.json` : une tâche par version et par cas, avec `description`, `modele` et
`consigne` (le texte exact à donner au sous-agent). Les copies de la skill n'ont pas leurs evals :
l'agent ne voit jamais les attentes.

## 3. Lancer les sous-agents

Lire `consignes.json`, puis, **dans un seul message**, lancer un sous-agent par tâche avec l'outil
Agent : `subagent_type: "general-purpose"`, `model` = le champ `modele` de la tâche, `description`
= le champ `description`, `prompt` = le champ `consigne`, tel quel. Ils tournent en arrière-plan ;
attendre leurs notifications de fin sans les interroger. Chaque agent écrit sa réponse au chemin
`reponse` de sa tâche.

Ne pas lancer plus d'une vingtaine d'agents à la fois ; au-delà, procéder par lots.

## 4. Noter et lire le rapport

Quand toutes les réponses sont écrites :

```
python3 scripts/evals_agents.py noter legistique-fr-workspace/evals-agents/<horodatage>
```

Chaque réponse est notée par `codex exec -m gpt-6.1-sol` (modifiable par `--modele`), avec la
consigne de juge et le schéma de `run_evals.py`. Le script écrit `resultats.json` et `rapport.md` :
un tableau des scores par cas et par version, puis les attentes non respectées avec la
justification du juge.

## 5. Interpréter

- Lire chaque attente manquée avant de conclure : une attente peut être mal formulée ou l'énoncé
  ambigu (une réponse juste au regard du guide peut être notée fausse). Corriger alors l'eval, le
  dire, et relancer le cas pour **toutes** les versions comparées.
- Un seul passage par cas : les écarts d'un point sont du bruit. Conclure sur la tendance et sur les
  défauts qualitatifs relevés par le juge.
- Reporter le résultat dans les notes de version (`distribution/notes/`), avec la méthode
  (« exécution par Sonnet, notation par GPT 6.1 Sol dans Codex »).
