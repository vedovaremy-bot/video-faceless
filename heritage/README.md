# Heritage — vidéo faceless (9:16, 34 s)

Vidéo finale : `heritage_promo.mp4` (1080×1920, 30 fps, musique originale générée).

Régénérer :
```
node render.js                 # images -> out/video_noaudio.mp4 + out/events.json
python3 music.py               # bande-son -> out/audio.wav
ffmpeg -y -i out/video_noaudio.mp4 -i out/audio.wav -c:v copy -c:a aac -b:a 192k -shortest heritage_promo.mp4
```
Textes et timings : `index.html` (ouvrable dans un navigateur pour un aperçu en boucle).
