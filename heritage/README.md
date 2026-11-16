# Héritage par IHC — vidéos faceless (9:16, DA noir & doré)

| Fichier | Format | Appel à l'action |
|---|---|---|
| `v1_flou.mp4` | Chaos de conseils → « STOP » → un seul plan (~36 s) | DM « HÉRITAGE » + like/abonne-toi |
| `v2_5points.mp4` | Liste « 5 points à vérifier avant d'acheter une formation » (~42 s) | Lien en bio **ou** DM |
| `v3_dm.mp4` | Conversation DM mise en scène + sous-titres karaoké (~39 s) | DM « HÉRITAGE » + like/abonne-toi |
| `heritage_promo.mp4` | Ancienne version (voix féminine) | Lien en bio |

Voix : homme, Coqui `tts_models/fr/css10/vits` (gratuit). ElevenLabs est prêt (`voice_el.py`) dès qu'une clé valide est configurée.

## Régénérer
```
./build2.sh v1_flou coqui 7          # COQUI_PY=<venv>/bin/python COQUI_MODEL=<dossier du modèle>
./build2.sh v1_flou <voice_id_elevenlabs>
SKIP_VOICE=1 ./build2.sh v3_dm coqui 23   # refait l'image/le son sans regénérer la voix
```
- Textes lus : `scripts/<video>.js` (champ `say` = orthographe pour la prononciation, `ls` = vitesse).
- Écrans : `videos/<video>.html` — chaque élément est calé sur un mot de la voix (`data-cue="p3.2"` = 3e mot de la phrase p3).
- Moteur commun : `shared/engine.js`, thème : `shared/theme.css`.
