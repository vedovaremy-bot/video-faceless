#!/usr/bin/env bash
# Full build: voice -> frames -> music -> mix. Usage: ./build.sh <kokoro.onnx> <voices.bin>
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p out
python3 voice.py "$1" "$2"
node render.js
python3 music.py
ffmpeg -loglevel error -y -i out/video_noaudio.mp4 -i out/voice.wav -i out/music.wav -filter_complex "
 [1:a]aresample=44100,highpass=f=80,equalizer=f=200:t=q:w=1:g=1.5,equalizer=f=3500:t=q:w=1.2:g=2.5,acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=2,aecho=0.8:0.5:35:0.06,volume=1.0,asplit=2[v][sc];
 [2:a]volume=0.45[m];
 [m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[md];
 [v][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest heritage_promo.mp4
echo "OK -> heritage_promo.mp4"
