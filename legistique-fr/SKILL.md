---
name: legistique-fr
description: >-
  Légistique française : rédige ou corrige des textes législatifs et réglementaires (loi, ordonnance,
  décret, arrêté, article de code) selon le Guide de légistique du Conseil d'Etat et du SGG. Deux
  fonctions : (1) transformer une description en prose (note, idée de réforme, mesure en langage
  courant) en projet de texte normatif en articles, avec un tableau expliquant chaque transformation ;
  (2) relire un projet de texte normatif et le corriger avec commentaires (structure, formules de
  modification, visas, entrée en vigueur, vocabulaire, typographie). À utiliser dès qu'on demande de
  rédiger, relire, corriger ou « mettre en forme juridique » un projet de loi, de décret, d'arrêté, un
  amendement, un article de code, un texte modificatif, des visas ou une entrée en vigueur, même sans
  le mot « légistique ». French legislative and regulatory drafting (legistics).
license: MIT
---

# Légistique française

Cette skill fait d'un agent un légiste : il transforme une intention en prose en texte normatif
français conforme aux usages du Journal officiel, ou il relit un projet de texte et le corrige en
expliquant chaque correction. Les règles viennent du Guide de légistique (4e édition, mise à jour 2026,
Conseil d'Etat et secrétariat général du Gouvernement) et d'un cours de légistique qui en reprend
l'essentiel. Les fiches du guide sont citées sous la forme « fiche 3.4.1 » pour que le lecteur puisse
vérifier.

Pourquoi ces règles comptent : un texte normatif est lu par des juges qui l'interprètent strictement
(une virgule mal placée a déjà fait tomber une épreuve de concours, CE 3 juillet 1959, Feldzer), par des
usagers qui doivent le comprendre sans le rédacteur, et par des rédacteurs futurs qui devront le
modifier sans le casser. Chaque règle ci-dessous protège l'un de ces trois lecteurs.

## Choisir la fonction

| Situation | Fonction |
|---|---|
| L'utilisateur fournit de la prose (note, description, liste de mesures, idée) et veut un texte normatif | **A. Rédaction** |
| L'utilisateur fournit un projet déjà rédigé en articles et veut une relecture, une correction, un avis | **B. Correction** |
| L'utilisateur fournit un texte déjà rédigé mais demande de le « réécrire » ou « refaire » | B, puis A pour les parties à reprendre entièrement |
| Question ponctuelle (comment formuler une abrogation, quel ordre pour les visas) | Répondre directement en s'appuyant sur les références |

Dans les deux fonctions, commencer par qualifier le texte, car presque toutes les règles en dépendent :

1. **Nature** : loi, ordonnance, décret (simple, en Conseil d'Etat, en conseil des ministres), arrêté,
   ou article destiné à un code. Si l'utilisateur ne le dit pas, déduire de la matière (article 34 de la
   Constitution pour le domaine de la loi, article 37 pour le règlement) et **énoncer l'hypothèse
   retenue** en tête de la réponse. Conséquences immédiates : une loi n'a ni visas ni article
   d'exécution ; un décret et un arrêté en ont ; les assemblées imposent « est ainsi rédigé » là où le
   règlement écrit « est remplacé par les dispositions suivantes ».
2. **Texte autonome ou modificatif** : avant de créer un texte nouveau, chercher le support existant
   (code, loi ou décret traitant de la même matière) où insérer les règles (fiche 3.4.1). Un texte
   modificatif obéit à une grammaire propre, voir `references/modifications-insertions.md`.
3. **Destinataires et situations en cours** : qui est touché, existe-t-il des procédures ou contrats en
   cours, une date commune d'entrée en vigueur s'impose-t-elle (textes applicables aux entreprises :
   1er janvier, avril, juillet, octobre).

## Fonction A : de la prose au texte normatif

### Étape 1 : extraire le contenu normatif

Lire la prose et dresser la liste des règles qu'elle contient, chacune sous la forme
« sujet, action, conditions, exceptions, sanction, date ». Séparer ce qui est normatif de ce qui ne
l'est pas : les justifications, objectifs, constats, souhaits et explications ne vont pas dans le
dispositif. Ils alimentent l'exposé des motifs (loi) ou la notice explicative (décret), que l'on peut
proposer en fin de réponse. Un dispositif qui explique ou souhaite n'oblige personne et donne prise
au contentieux.

Relever les trous : autorité compétente non désignée, délai sans point de départ, sanction sans
échelle, « etc. » ou « notamment » qui cachent une liste incomplète, régime transitoire absent. Ces
trous deviennent des **points à arbitrer** dans la réponse, jamais des inventions silencieuses.

### Étape 2 : bâtir le plan

Appliquer `references/structure-et-plan.md`. En résumé :

- Traiter d'abord l'objet principal (« Dispositions générales » : objet, champ, définitions), puis les
  dispositions communes avant les dispositions particulières, puis les dispositions pénales, puis les
  « Dispositions transitoires et finales » (entrée en vigueur, abrogations, coordinations).
- Une règle par article. Mieux vaut dix articles courts qu'un article à six paragraphes.
- Articles seuls pour un texte court. Un niveau de division : chapitres. Deux : chapitres et sections.
  Trois : titres, chapitres, sections. Parties et livres sont réservés aux codes.
- Texte modificatif : suivre l'ordre des articles du texte modifié, une division par texte modifié, ne
  jamais toucher deux fois au même article dans le même texte modificatif.

### Étape 3 : rédiger

Appliquer `references/langue-et-style.md` et `references/typographie.md`. Les réflexes les plus
rentables :

- **Présent de l'indicatif à valeur impérative.** « Les fédérations transmettent », pas « doivent
  transmettre » ni « transmettront ». Le mot « doit » n'ajoute rien et « impérativement » encore moins.
- **Phrases courtes, une idée par alinéa**, énumérations en 1°, 2° puis a), b). Pas de « et/ou »,
  pas de « le ou les », pas de doubles négations, pas d'abréviations, sigles, parenthèses ou notes.
- **Désigner par la fonction, pas par la personne** : « le ministre chargé de la santé » (sauf justice,
  intérieur, défense, affaires étrangères), « l'autorité administrative » dans une loi.
- **Mots à sens précis** : autorité / tutelle, conformité / compatibilité, suspendre / interrompre,
  dispositions (acte unilatéral) / stipulations (contrat, traité), « sous réserve » (prééminence) /
  « sans préjudice » (cumul) / « par dérogation » (exception ciblée). Le mot « notamment » est banni
  dans la définition d'une interdiction ou d'une sanction.
- **Renvois** : « mentionné à l'article 3 », jamais « visé » (réservé aux visas) ni « article 3 de la
  présente loi » (sauf ambiguïté entre plusieurs textes). Renvoyer de préférence à un régime
  (« recouvrées comme les créances de l'Etat étrangères à l'impôt ») plutôt qu'à des numéros.
- **Renvois au règlement** : une loi renvoie à « un décret en Conseil d'Etat » ou « par voie
  réglementaire » et ne fixe pas l'autorité ministérielle compétente. Un décret peut renvoyer à un
  arrêté, mais de façon précise et encadrée, jamais pour « fixer les modalités d'application du présent
  décret » (fiche 3.5.3).
- **Entrée en vigueur** : par défaut, lendemain de la publication ; si les destinataires doivent
  s'adapter, différer (« Le présent décret entre en vigueur le 1er janvier 2027 » ou « le premier jour
  du troisième mois suivant sa publication ») et prévoir le sort des situations en cours. Une loi ne
  renvoie jamais à un décret le soin de fixer sa date sans borne (« à une date fixée par décret et au
  plus tard le… »).
- **Formules d'encadrement** : intitulé, visas, « Décrète : », article d'exécution, selon
  `references/formules-et-modeles.md`. Ne pas inventer un numéro NOR ni un numéro de texte : laisser
  « n° … du … ».

### Étape 4 : livrer

Structure de réponse à respecter, dans cet ordre :

```
## Hypothèses retenues
(nature du texte, support, ce qui a été déduit ; 3 à 6 lignes)

## Projet de texte
(le texte, avec la présentation du Journal officiel : intitulé, visas si décret ou arrêté,
« Article 1er », divisions, article d'exécution)

## Tableau des transformations
| Passage de la prose | Devenu | Règle appliquée | Pourquoi |
(une ligne par règle ou passage notable ; citer la fiche du guide dans la colonne « Règle »)

## Points à arbitrer
(liste numérotée : chaque choix que le rédacteur doit confirmer ou compléter)

## Contenu écarté du dispositif
(ce qui relève de l'exposé des motifs ou de la notice, avec une proposition de notice si le texte
est un décret : Publics concernés / Objet / Entrée en vigueur / Application)
```

Le tableau des transformations est la partie pédagogique demandée : il doit permettre à un lecteur de
comprendre pourquoi « les entreprises devront obligatoirement déclarer » est devenu « Les entreprises
déclarent ». Regrouper les changements répétitifs (par exemple « futur remplacé par le présent, 7
occurrences ») plutôt que de les lister un par un.

## Fonction B : correction commentée d'un texte normatif

### Étape 1 : lire en légiste

Passer le texte au crible de `references/grille-de-relecture.md`, dans cet ordre, car les erreurs de
structure se corrigent avant celles de langue :

1. **Qualification et compétence** : nature du texte, niveau de norme cohérent avec le contenu (une
   loi qui fixe l'organisation d'une commission empiète sur le règlement ; un décret qui crée une
   sanction pénale au-delà de la contravention empiète sur la loi), renvois vers le bas ou vers le haut.
2. **Structure** : plan, divisions, numérotation, une règle par article, place des dispositions
   transitoires et finales, article d'exécution en dernier.
3. **Encadrement** : intitulé (objet essentiel, sans référence au texte modifié), visas (textes à
   viser, ordre hiérarchique puis chronologique, « modifié », consultations, Conseil d'Etat), formule
   d'ouverture, article d'exécution.
4. **Grammaire des modifications** (si texte modificatif) : « est remplacé par les dispositions
   suivantes », « ainsi rédigé » pour les insertions, « abrogé » pour un texte ou une division,
   « supprimé » pour un alinéa, une phrase ou des mots, désignation exacte des passages, ordre des
   articles, référence au texte en vigueur, « susvisé » seulement si le texte figure dans les visas
   d'origine et jamais dans un code.
5. **Entrée en vigueur et situations en cours** : disposition présente et placée avant l'article
   d'exécution, différé suffisant, sort des procédures et contrats en cours, abrogations explicites.
6. **Langue** : temps, « doit », mots passe-partout, « ledit », préfixe « sus », anglicismes, latin,
   « notamment », locutions d'articulation, sigles, parenthèses.
7. **Typographie** : « Article 1er », 1° 2° a) b), guillemets français, « premier alinéa », nombres,
   ponctuation des énumérations, intitulés de divisions sans point final.

### Étape 2 : corriger avec économie

Le guide impose un principe d'économie (fiche 3.4.1) : on ne réécrit pas ce qui fonctionne, on ne
touche pas à la typographie ou à la ponctuation d'un texte ancien sans nécessité, et l'on ne modifie
jamais un choix de fond (seuil, délai, autorité compétente) sans le signaler comme une question, pas
comme une correction. Distinguer donc trois niveaux :

- **Bloquant** : illégalité ou inintelligibilité probable (incompétence, renvoi interdit, date d'entrée
  en vigueur laissée à un décret sans borne, « toutes dispositions contraires sont abrogées »,
  « notamment » dans une interdiction sanctionnée, article modifié deux fois).
- **Recommandé** : règle du guide non respectée, sans risque contentieux immédiat (futur, « doit »,
  « ledit », sigle, alinéa désigné par un chiffre, ordre des visas).
- **Style** : améliorations facultatives.

### Étape 3 : livrer

```
## Diagnostic
(nature du texte, impression d'ensemble, 3 à 8 lignes, les points bloquants d'abord)

## Texte corrigé
(texte intégral corrigé, présentation Journal officiel ; les passages modifiés peuvent être signalés
en gras si l'utilisateur travaille en Markdown, sinon texte propre)

## Commentaires
| N° | Emplacement | Constat | Correction | Règle (fiche) | Niveau |
(numéroté, dans l'ordre du texte ; Niveau = Bloquant / Recommandé / Style)

## Questions au rédacteur
(choix de fond à confirmer, informations manquantes : dates, consultations, ministres rapporteurs)
```

Si le texte est long, on peut placer un renvoi numéroté « [3] » dans le texte corrigé à l'endroit de
chaque commentaire. Ne jamais livrer les commentaires sans le texte corrigé, ni l'inverse.

## Références

Lire le fichier utile au moment utile ; ils sont conçus pour être lus indépendamment. Commencer
toujours par ces fiches de synthèse.

| Fichier | Contenu | Quand le lire |
|---|---|---|
| `references/structure-et-plan.md` | Plans consacrés, ordre des rubriques, divisions, article, alinéas, énumérations, numérotation, insertion d'articles | Fonction A étape 2, fonction B point 2 |
| `references/langue-et-style.md` | Temps et mode, phrases, vocabulaire à sens précis, mots proscrits, « notamment », locutions d'articulation, désignation des autorités, renvois, féminisation | Fonction A étape 3, fonction B point 6 |
| `references/modifications-insertions.md` | Formules de modification, insertion, remplacement, suppression, abrogation ; techniques de présentation ; visas et « susvisé » ; renvois au droit positif | Tout texte modificatif |
| `references/formules-et-modeles.md` | Intitulé, squelettes complets de loi, ordonnance, décret, arrêté ; visas (quoi viser, ordre, rédaction) ; article d'exécution ; entrée en vigueur ; situations en cours ; abrogations ; renvois au règlement ; notice explicative | Fonction A étape 3, fonction B points 3 et 5 |
| `references/typographie.md` | Règles typographiques du Journal officiel | Mise au propre finale, fonction B point 7 |
| `references/grille-de-relecture.md` | Liste de contrôle ordonnée avec niveaux de gravité | Fonction B, et autocontrôle en fin de fonction A |

### Guide complet : source subsidiaire

`references/guide/` contient le texte intégral du Guide de légistique, une fiche par fichier
(101 fichiers, environ 360 000 mots), avec un index `references/guide/index.md`. Les fiches ci-dessus
en sont la synthèse et suffisent dans la plupart des cas : le guide complet ne sert qu'à **préciser**.

Le consulter seulement quand :

- une question sort du champ des fiches de synthèse : procédure d'élaboration (quelles consultations
  sont obligatoires, saisine du Conseil d'Etat, contreseings, signature, publication), application
  outre-mer, Alsace-Moselle, Corse, lois de finances et de financement de la sécurité sociale, textes
  internationaux et européens, mesures individuelles et nominations ;
- le texte relève d'un cas pratique du guide (partie 5 : services de l'Etat, organisme consultatif,
  établissement public, GIP, régime d'autorisation, sanctions, prélèvement fiscal, redevance, statuts
  des personnels, expérimentation), qui fournit des modèles de rédaction ;
- une fiche de synthèse renvoie à une fiche du guide sans en donner le détail, ou l'utilisateur
  demande ce que dit exactement le guide.

Méthode, pour ne pas saturer le contexte :

1. Repérer la fiche dans `references/guide/index.md` ou chercher un mot-clé dans le dossier.
2. Lister les titres de la fiche (lignes commençant par `#`) et ne lire que la section utile. Une
   fiche de plus de 5 000 mots ne se lit jamais en entier ; une ou deux fiches par question suffisent.
3. Citer la fiche (« fiche 3.6.1 ») et, si la règle vient du guide complet, le dire.
4. Les fichiers sont extraits automatiquement du PDF : si un tableau paraît incohérent, ne pas s'y
   fier et renvoyer au guide sur Légifrance. Chaque fiche porte sa date de mise à jour ; le droit
   positif cité en exemple a pu évoluer depuis.

## Garde-fous

- Ne pas inventer de droit positif : si un renvoi à un article de code est nécessaire et que le numéro
  n'est pas connu avec certitude, écrire « l'article L. … du code … » et le signaler dans les points à
  arbitrer. Un numéro plausible mais faux est pire qu'un blanc.
- Ne pas fabriquer de numéro NOR, de numéro de décret, de date de signature, de nom de ministre.
- Ne pas trancher les questions de fond (seuils, montants, autorité compétente, sanctions) à la place
  du rédacteur : proposer, marquer entre crochets, lister dans les points à arbitrer.
- Le guide distingue lois et règlements sur plusieurs formules ; quand la nature du texte est
  incertaine, donner la formule des deux régimes plutôt que d'en choisir une au hasard.
- Un texte modificatif se rédige par rapport au texte **en vigueur** et consolidé ; si l'utilisateur ne
  fournit pas le texte modifié, le demander ou signaler que les désignations d'alinéas n'ont pas pu
  être vérifiées.
