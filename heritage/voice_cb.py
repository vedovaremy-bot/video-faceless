"""Voice-over with Chatterbox (free, local) using the owner's own voice as reference.
Usage: python3 voice_cb.py <scripts/vX.js> <outDir> <reference.wav>
Env: CB_PY (Chatterbox venv python), CB_SPEED (default 1.12), PAUSE_SCALE (0.7), TAIL (0.8).
1) cb_gen.py generates each phrase in the Chatterbox venv,
2) each phrase is sped up (pitch kept) and trimmed,
3) word timings come from a faster-whisper transcription of each phrase (Chatterbox gives none),
-> <outDir>/voice.wav + timing.json, same format as voice_el.py."""
import sys, os, json, re, subprocess, unicodedata, wave
import numpy as np
from faster_whisper import WhisperModel

script_file, out_dir, ref = sys.argv[1:4]
CB_PY = os.environ["CB_PY"]; SPEED = float(os.environ.get("CB_SPEED", "1.12")); SR = 24000
src = open(script_file, encoding="utf-8").read(); SCRIPT = json.loads(src[src.index("["):src.rindex("]") + 1])
SAY = [(r"[«»]", ""), (r"\bGO\b", "go"), (r"\bDM\b", "dé èm"), (r"…", ","), (r"\bS\b(?= :)", "S")]
def spoken(s):
    for a, b in SAY: s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()
def norm(w):
    w = unicodedata.normalize("NFD", w.lower()); w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9']", "", w)

cb_dir = os.path.join(out_dir, "cb"); os.makedirs(cb_dir, exist_ok=True)
jobs = [{"id": p["id"], "text": spoken(p.get("say", p["text"])), "out": os.path.abspath(f"{cb_dir}/{p['id']}.wav"),
         "exaggeration": 0.7 if p.get("ls", 1) < 0.85 else 0.6} for p in SCRIPT]
# only (re)generate phrases whose text changed since the last run (Chatterbox is slow on CPU)
def unchanged(j):
    t = j["out"] + ".txt"
    return os.path.exists(j["out"]) and os.path.exists(t) and open(t, encoding="utf-8").read() == j["text"]
todo = [j for j in jobs if not unchanged(j)]
json.dump(todo, open(f"{cb_dir}/jobs.json", "w"))
if todo: subprocess.run([CB_PY, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cb_gen.py"), f"{cb_dir}/jobs.json", ref],
               check=True, env={**os.environ, "HF_HUB_DISABLE_XET": "1"})
for j in jobs: open(j["out"] + ".txt", "w", encoding="utf-8").write(j["text"])

wm = WhisperModel("small", device="cpu", compute_type="int8")
def load(path, speed):
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-af", f"atempo={speed}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).copy()
def align(tokens, marks):
    times, j = [None] * len(tokens), 0
    for i, tok in enumerate(tokens):
        nt = norm(tok)
        if not nt: continue
        for k in range(j, min(j + 4, len(marks))):
            nm = norm(marks[k][1])
            if nm and (nm == nt or nm in nt or nt in nm or nm[:4] == nt[:4]):
                times[i] = marks[k][0]; j = k + 1; break
    known = [(i, t) for i, t in enumerate(times) if t is not None] or [(0, 0.0)]
    for i in range(len(times)):
        if times[i] is None:
            prev = max([k for k in known if k[0] < i], default=None, key=lambda k: k[0])
            nxt = min([k for k in known if k[0] > i], default=None, key=lambda k: k[0])
            if prev and nxt: times[i] = prev[1] + (nxt[1] - prev[1]) * (i - prev[0]) / (nxt[0] - prev[0])
            else: times[i] = prev[1] if prev else (nxt[1] if nxt else 0.0)
    return times

chunks, phrases, cur = [np.zeros(int(0.1 * SR), np.float32)], {}, 0.1
for p in SCRIPT:
    a = load(f"{cb_dir}/{p['id']}.wav", SPEED + (0.06 if p.get("ls", 1) < 0.85 else 0))
    env = np.convolve(np.abs(a), np.ones(480) / 480, "same")   # trim on a smoothed envelope: drops trailing breath/hiss
    nz = np.where(env > 0.012 * np.max(env))[0]
    a = a[max(0, nz[0] - int(0.08 * SR)): nz[-1] + int(0.1 * SR)]
    a = a / max(1e-6, np.max(np.abs(a))) * 0.9; L = len(a) / SR
    a16 = np.interp(np.arange(0, len(a), SR / 16000), np.arange(len(a)), a).astype(np.float32)
    segs, _ = wm.transcribe(a16, language="fr", word_timestamps=True, vad_filter=False)
    marks = [(w.start, w.word.strip()) for s in segs for w in s.words]
    words = [round(cur + t, 3) for t in align(p["text"].split(), marks)]
    phrases[p["id"]] = {"start": round(cur, 3), "end": round(cur + L, 3), "words": words}
    pause = p.get("pause", 0.3) * float(os.environ.get("PAUSE_SCALE", "0.7"))
    chunks += [a, np.zeros(int(pause * SR), np.float32)]; cur += L + pause
    print(p["id"], f"{L:.2f}s", "|", " ".join(m[1] for m in marks), flush=True)
tail = float(os.environ.get("TAIL", "0.8"))
out = np.concatenate(chunks + [np.zeros(int(tail * SR), np.float32)])
w = wave.open(f"{out_dir}/voice.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes()); w.close()
json.dump({"phrases": phrases, "duration": round(cur + tail, 3)}, open(f"{out_dir}/timing.json", "w"))
print("duration", round(cur + tail, 2))
