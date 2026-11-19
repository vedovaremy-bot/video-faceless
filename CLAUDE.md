# Projet vidéos faceless (affiliation / Héritage)

## Stratégie de contenu : 3 types de vidéos
Le but : qualifier les prospects sur plusieurs vidéos **buzz** et **valeur**, pour qu'ils passent à l'action et achètent la formation lors d'une vidéo **promotion**.

| Type | Objectif | Héritage mentionné ? |
|---|---|---|
| **Buzz** | Attirer : hook très fort, sujet qui fait réagir (affiliation, e-commerce, business en ligne) | **Non, jamais** |
| **Valeur** | Éduquer et créer la confiance : conseils concrets, erreurs à éviter, méthodes | **Non, jamais** |
| **Promotion** | Convertir : présenter la formation Héritage, ce qu'elle contient, pour qui | **Oui, uniquement ici** |

## Appel à l'action
- Fin de vidéo : « écris-moi GO » ou « envoie-moi GO » en DM. Ne plus dire « HÉRITAGE » à la fin.
- **Buzz et Valeur** : « Écris-moi GO en DM, et je te dis par où commencer. » (le propriétaire présente ensuite Héritage en DM).
- **Promotion** : GO en DM pour recevoir le lien / les infos sur la formation.
- **Un seul appel à l'action, à la fin : GO en DM.** Pas de « abonne-toi » en fin de vidéo (retour de la communauté : ça dilue le passage à l'action).
- Si un « abonne-toi » est voulu, le placer au début de la vidéo, jamais à la fin, et seulement si c'est vrai (ex. « je partage une vidéo tous les jours »).
- Formulation de fin conseillée : « Si toi aussi tu veux te lancer dans l'affiliation, écris-moi / envoie-moi GO en DM… » (jamais « gagner un revenu » : promesse de gains).

## Style
- **Voix off par défaut : ElevenLabs, voice ID `3Tp5mYhT9wrfnry9pzvV`** (voix de la bibliothèque, choisie par le propriétaire) : `./build2.sh <video> 3Tp5mYhT9wrfnry9pzvV <seed>` dans `heritage/`. Débit ×1,1 (hook ×1,18), pauses courtes. Clé API via le proxy (abonnement Creator, ~2 000 caractères par vidéo).
- Ne jamais cloner ni copier cette voix hors d'ElevenLabs (voix d'un comédien réel, interdit par les CGU).
- **La voix doit aller jusqu'au bout** : chaque rendu se termine par `check_voice.py` (transcription automatique) qui vérifie que chaque phrase est dite en entier, et que la vidéo s'arrête peu après le dernier mot (blanc final ≈ 0,8 s).
- Chatterbox (voix du propriétaire clonée) testé et **refusé** : ne plus le proposer, rester sur ElevenLabs.
- Voix de secours : Microsoft « Henri » (`./build2.sh <video> henri`).
- DA : noir & doré (`heritage/shared/theme.css`), hook fort dans les 3 premières secondes, formats variés.
- Ne pas parler de prix, aucune promesse de gains ; garder les mentions « lien affilié · aucun résultat garanti » quand un lien est évoqué.
