"""Voice-over with Microsoft neural voice fr-FR-HenriNeural (via edge-tts), phrase by phrase,
with exact word timings from the service's WordBoundary events.
Usage: python3 voice_edge.py <scripts/vX.js> <outDir> [voice]
Writes <outDir>/voice.wav + <outDir>/timing.json (same format as voice_el.py).
In this container: export SSL_CERT_FILE=/root/.ccr/ca-bundle.crt (the HTTPS proxy is read from $HTTPS_PROXY)."""
import sys, os, json, re, asyncio, subprocess, unicodedata, wave
import numpy as np
import edge_tts

script_file, out_dir = sys.argv[1:3]
VOICE = sys.argv[3] if len(sys.argv) > 3 else "fr-FR-HenriNeural"
PROXY = os.environ.get("HTTPS_PROXY") or None
SR = 24000
src = open(script_file, encoding="utf-8").read()
SCRIPT = json.loads(src[src.index("["):src.rindex("]") + 1])
SAY = [(r"[«»]", ""), (r"\bGO\b", "go"), (r"HÉRITAGE", "Héritage"), (r"\b[Ll]ike\b", "laïke")]
def spoken(s):
    for a, b in SAY: s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()
def norm(w):
    w = unicodedata.normalize("NFD", w.lower()); w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9']", "", w)

async def synth(text, rate):
    com = edge_tts.Communicate(text, VOICE, rate=rate, proxy=PROXY, boundary="WordBoundary")
    audio, marks = bytearray(), []
    async for ch in com.stream():
        if ch["type"] == "audio": audio += ch["data"]
        elif ch["type"] == "WordBoundary": marks.append((ch["offset"] / 1e7, ch["text"]))
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "-", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         input=bytes(audio), capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).copy(), marks

def align(tokens, marks, L):
    """time for each display token: walk the spoken words in order, matching by normalized text."""
    times, j = [None] * len(tokens), 0
    for i, tok in enumerate(tokens):
        nt = norm(tok)
        if not nt: continue
        for k in range(j, min(j + 4, len(marks))):
            nm = norm(marks[k][1])
            if nm and (nm == nt or nt.startswith(nm) or nm.startswith(nt) or nm in nt or nt in nm):
                times[i] = marks[k][0]; j = k + 1; break
    # fill gaps (punctuation tokens, unmatched words) from neighbours
    known = [(i, t) for i, t in enumerate(times) if t is not None] or [(0, 0.0)]
    for i in range(len(times)):
        if times[i] is None:
            prev = max([k for k in known if k[0] < i], default=None, key=lambda k: k[0])
            nxt = min([k for k in known if k[0] > i], default=None, key=lambda k: k[0])
            if prev and nxt:  # spread unmatched words evenly between their matched neighbours
                times[i] = prev[1] + (nxt[1] - prev[1]) * (i - prev[0]) / (nxt[0] - prev[0])
            else:
                times[i] = prev[1] if prev else (nxt[1] if nxt else 0.0)
    return times

chunks, phrases, cur = [np.zeros(int(0.1 * SR), np.float32)], {}, 0.1
for p in SCRIPT:
    # pace: faster, more energetic delivery (hook phrase even faster); VOICE_RATE / HOOK_RATE env vars override
    rate = p.get("rate") or (os.environ.get("HOOK_RATE", "+26%") if p.get("ls", 1) < 0.85 else os.environ.get("VOICE_RATE", "+18%"))
    a, marks = asyncio.run(synth(spoken(p.get("say", p["text"])), rate))
    nz = np.where(np.abs(a) > 0.01)[0]
    a0 = max(0, nz[0] - int(0.03 * SR)); a1 = min(len(a), nz[-1] + int(0.12 * SR))
    lead = a0 / SR; a = a[a0:a1]; L = len(a) / SR
    marks = [(max(0.0, t - lead), w) for t, w in marks]
    times = align(p["text"].split(), marks, L)
    words = [round(cur + t, 3) for t in times]
    phrases[p["id"]] = {"start": round(cur, 3), "end": round(cur + L, 3), "words": words}
    pause = p.get("pause", 0.3) * float(os.environ.get("PAUSE_SCALE", "0.7"))  # tighter gaps between phrases
    chunks += [a, np.zeros(int(pause * SR), np.float32)]; cur += L + pause
    print(p["id"], f"{L:.2f}s", len(marks), "mots", flush=True)
tail = 1.6
out = np.concatenate(chunks + [np.zeros(int(tail * SR), np.float32)])
out = out / max(1e-6, np.max(np.abs(out))) * 0.9
w = wave.open(f"{out_dir}/voice.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes()); w.close()
json.dump({"phrases": phrases, "duration": round(cur + tail, 3)}, open(f"{out_dir}/timing.json", "w"))
print("duration", round(cur + tail, 2))
