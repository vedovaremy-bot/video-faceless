#!/usr/bin/env bash
# Build one video:
#   ./build2.sh <name> tom [music_seed]          Piper voice Tom (needs PIPER_MODEL env var)
#   ./build2.sh <name> coqui [music_seed]        free male voice (needs COQUI_PY + COQUI_MODEL env vars)
#   ./build2.sh <name> <elevenlabs_voice_id> [music_seed]
#   name = v1_flou | v2_5points | v3_dm   -> <name>.mp4
set -euo pipefail
cd "$(dirname "$0")"
name=$1; voice=$2; seed=${3:-7}; out=out/$name; mkdir -p "$out"
if [ -n "${SKIP_VOICE:-}" ]; then
  echo "reusing $out/voice.wav"
elif [ "$voice" = tom ]; then
  python3 voice_piper.py "scripts/$name.js" "$out" "${PIPER_MODEL:?path to fr_FR-tom-medium.onnx}"
elif [ "$voice" = coqui ]; then
  "${COQUI_PY:?path to the venv python with coqui-tts}" voice_coqui.py "scripts/$name.js" "$out" "${COQUI_MODEL:?dir of tts_models--fr--css10--vits}"
else
  python3 voice_el.py "scripts/$name.js" "$out" "$voice"
fi
node render2.js "videos/$name.html" "$out"
dur=$(python3 -c "import json;print(json.load(open('$out/timing.json'))['duration'])")
python3 music2.py "$out" "$dur" "$seed"
ffmpeg -loglevel error -y -i "$out/video_noaudio.mp4" -i "$out/voice.wav" -i "$out/music.wav" -filter_complex "
 [1:a]aresample=44100,highpass=f=70,equalizer=f=140:t=q:w=1:g=3,equalizer=f=3200:t=q:w=1.2:g=2.5,acompressor=threshold=-20dB:ratio=3.5:attack=5:release=80:makeup=3,aecho=0.8:0.4:30:0.05,asplit=2[v][sc];
 [2:a]volume=0.5[m];
 [m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=300[md];
 [v][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "$name.mp4"
echo "OK -> $name.mp4"
