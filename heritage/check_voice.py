"""Check that the finished video says the whole script, up to the last word.
Usage: python3 check_voice.py <video.mp4> <scripts/vX.js>
Transcribes the video's audio (faster-whisper, French) and checks each phrase's last words are heard, in order,
and that speech goes on to (almost) the end of the video. Exit code 1 if something is missing."""
import sys, json, re, unicodedata, subprocess
from faster_whisper import WhisperModel
video, script_file = sys.argv[1:3]
src = open(script_file, encoding="utf-8").read(); SCRIPT = json.loads(src[src.index("["):src.rindex("]") + 1])
def norm(s):
    s = unicodedata.normalize("NFD", s.lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s.replace("'", " "))
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video], capture_output=True, text=True).stdout)
m = WhisperModel("small", device="cpu", compute_type="int8")
import numpy as np
pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
segs, _ = m.transcribe(np.frombuffer(pcm, np.float32), language="fr", word_timestamps=True, vad_filter=False)
words = [(w.start, w.end, norm(w.word).strip()) for s in segs for w in s.words]
heard = " ".join(w for _, _, w in words)
print("Transcription :", heard)
ok, pos = True, 0
for p in SCRIPT:
    sing = lambda w: w[:-1] if len(w) > 3 and w[-1] in "sx" else w   # plural vs singular sound the same in French
    tail = [sing(w) for w in norm(p["text"]).split()[-3:]]          # last 3 words of each phrase
    hits = [i for i, t in enumerate(tail) if f" {t}" in f" {heard[pos:]} "]  # prefix match: "lien" ~ "liens" (homophones)
    found = len(hits) >= 2
    print(f"{p['id']}: fin « {' '.join(tail)} » -> {'OK' if found else 'MANQUANT'}")
    ok &= found
    if found:
        k = heard.find(tail[hits[-1]], pos); pos = k if k >= 0 else pos
last_end = words[-1][1] if words else 0
print(f"Dernier mot entendu à {last_end:.1f}s, vidéo de {dur:.1f}s")
if dur - last_end > 2.0: print("ATTENTION : plus de 2 s sans voix à la fin"); ok = False
print("RESULTAT :", "OK, la voix va jusqu'au bout" if ok else "PROBLEME")
sys.exit(0 if ok else 1)
