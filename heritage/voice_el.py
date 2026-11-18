"""ElevenLabs voice-over, phrase by phrase, with exact word timings (character alignment from the API).
Usage: python3 voice_el.py <scripts/vX.js> <outDir> <voice_id>
Writes <outDir>/voice.wav + <outDir>/timing.json ({phrases: {id: {start, end, words}}, duration}) for render2.js.
The API key is injected by the session's network proxy (header xi-api-key); nothing to configure here.
Env: EL_SPEED (default 1.1, max 1.2), EL_MODEL (default eleven_multilingual_v2), PAUSE_SCALE (default 0.7)."""
import sys, os, json, re, base64, wave, unicodedata, urllib.request, urllib.error
import numpy as np

script_file, out_dir, voice_id = sys.argv[1:4]
SR = 24000
MODEL = os.environ.get("EL_MODEL", "eleven_multilingual_v2")
SPEED = float(os.environ.get("EL_SPEED", "1.1"))
src = open(script_file, encoding="utf-8").read()
SCRIPT = json.loads(src[src.index("["):src.rindex("]") + 1])
SAY = [(r"[«»]", ""), (r"\bGO\b", "go"), (r"HÉRITAGE", "Héritage"), (r"\bDM\b", "DM")]
def spoken(s):
    for a, b in SAY: s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()
def norm(w):
    w = unicodedata.normalize("NFD", w.lower()); w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9']", "", w)

def tts(text, prev, nxt, speed):
    body = {"text": text, "model_id": MODEL, "previous_text": prev, "next_text": nxt,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True, "speed": speed}}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=pcm_24000",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "xi-api-key": "proxy-injected"})
    d = None
    for attempt in range(5):  # the API is sometimes slow or returns 5xx: retry instead of failing
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60)); break
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429: sys.exit(f"ElevenLabs error {e.code}: {e.read().decode()[:300]}")
            print(f"  retry ({e.code})", flush=True)
        except Exception as e:
            print(f"  retry ({type(e).__name__})", flush=True)
        __import__("time").sleep(3 * (attempt + 1))
    if d is None: sys.exit("ElevenLabs unreachable after 5 attempts")
    pcm = np.frombuffer(base64.b64decode(d["audio_base64"]), dtype="<i2").astype(np.float32) / 32768
    al = d["alignment"]
    # characters -> spoken words with their start time
    marks, cur, t0 = [], "", None
    for ch, st in zip(al["characters"], al["character_start_times_seconds"]):
        if ch.isspace():
            if cur: marks.append((t0, cur)); cur = ""
        else:
            if not cur: t0 = st
            cur += ch
    if cur: marks.append((t0, cur))
    return pcm, marks

def align(tokens, marks):
    times, j = [None] * len(tokens), 0
    for i, tok in enumerate(tokens):
        nt = norm(tok)
        if not nt: continue
        for k in range(j, min(j + 4, len(marks))):
            nm = norm(marks[k][1])
            if nm and (nm == nt or nm in nt or nt in nm):
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
for i, p in enumerate(SCRIPT):
    prev = " ".join(spoken(q["text"]) for q in SCRIPT[max(0, i - 2):i])
    nxt = spoken(SCRIPT[i + 1]["text"]) if i + 1 < len(SCRIPT) else ""
    speed = min(1.2, SPEED + (0.08 if p.get("ls", 1) < 0.85 else 0))  # hook phrase a bit faster
    a, marks = tts(spoken(p.get("say", p["text"])), prev, nxt, speed)
    nz = np.where(np.abs(a) > 0.01)[0]
    a0 = max(0, nz[0] - int(0.03 * SR)); a1 = min(len(a), nz[-1] + int(0.12 * SR))
    lead = a0 / SR; a = a[a0:a1]; L = len(a) / SR
    marks = [(max(0.0, t - lead), w) for t, w in marks]
    words = [round(cur + t, 3) for t in align(p["text"].split(), marks)]
    phrases[p["id"]] = {"start": round(cur, 3), "end": round(cur + L, 3), "words": words}
    pause = p.get("pause", 0.3) * float(os.environ.get("PAUSE_SCALE", "0.7"))
    chunks += [a, np.zeros(int(pause * SR), np.float32)]; cur += L + pause
    print(p["id"], f"{L:.2f}s", flush=True)
tail = float(os.environ.get("TAIL", "0.8"))  # short silent tail: the video ends right after the last word
out = np.concatenate(chunks + [np.zeros(int(tail * SR), np.float32)])
out = out / max(1e-6, np.max(np.abs(out))) * 0.9
w = wave.open(f"{out_dir}/voice.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes()); w.close()
json.dump({"phrases": phrases, "duration": round(cur + tail, 3)}, open(f"{out_dir}/timing.json", "w"))
print("duration", round(cur + tail, 2))
