# Héritage par IHC — vidéo faceless (9:16, ~50 s, voix off)

Vidéo finale : `heritage_promo.mp4` (1080×1920, 30 fps). DA noir & doré (logo H couronné, Cinzel, satin noir/doré, poussière dorée).
Voix off : Kokoro (open source), voix française `ff_siwis`. Musique : générée (originale, libre de droits).

Régénérer tout (après modification des textes) :
```
pip install kokoro-onnx soundfile
# modèles : https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
./build.sh kokoro-v1.0.int8.onnx voices-v1.0.bin
```
- Texte lu : `voice.py` (liste SCRIPT) — les animations se recalent automatiquement sur la voix.
- Textes à l'écran et design : `index.html`.
