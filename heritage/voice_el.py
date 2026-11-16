"""ElevenLabs voice-over, phrase by phrase, with word timestamps.
Usage: python3 voice_el.py <scripts/vX.js> <outDir> <voice_id>
Writes <outDir>/voice.wav and <outDir>/timing.json ({phrases: {id: {start, end, words}}, duration}) for render2.js.
The API key is injected by the session's network proxy (header xi-api-key)."""
import sys, json, base64, wave, urllib.request
import numpy as np

script_file, out_dir, voice_id = sys.argv[1:4]
SR = 24000
src = open(script_file, encoding='utf-8').read()
SCRIPT = json.loads(src[src.index('['):src.rindex(']') + 1])
SETTINGS = {"stability": 0.4, "similarity_boost": 0.8, "style": 0.45, "use_speaker_boost": True, "speed": 1.06}

def tts(text, prev, nxt):
    body = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": SETTINGS,
            "previous_text": prev, "next_text": nxt, "language_code": "fr"}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps?output_format=pcm_24000",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "xi-api-key": "proxy-injected"})
    d = json.load(urllib.request.urlopen(req, timeout=120))
    pcm = np.frombuffer(base64.b64decode(d["audio_base64"]), dtype="<i2").astype(np.float32) / 32768
    return pcm, d["alignment"]

chunks, phrases, cur = [np.zeros(int(0.12 * SR), np.float32)], {}, 0.12
for i, p in enumerate(SCRIPT):
    prev = " ".join(q["text"] for q in SCRIPT[max(0, i - 2):i])
    nxt = SCRIPT[i + 1]["text"] if i + 1 < len(SCRIPT) else ""
    audio, al = tts(p["text"], prev, nxt)
    # trim leading/trailing silence
    nz = np.where(np.abs(audio) > 0.01)[0]
    a0 = max(0, nz[0] - int(0.03 * SR)); a1 = min(len(audio), nz[-1] + int(0.12 * SR))
    lead = a0 / SR
    audio = audio[a0:a1]
    starts, chars = al["character_start_times_seconds"], al["characters"]
    text = "".join(chars)
    words, pos = [], 0
    for tok in p["text"].split():
        k = text.find(tok, pos); k = pos if k < 0 else k
        words.append(round(cur + max(0.0, starts[min(k, len(starts) - 1)] - lead), 3)); pos = k + len(tok)
    phrases[p["id"]] = {"start": words[0], "end": round(cur + len(audio) / SR, 3), "words": words}
    chunks += [audio, np.zeros(int(p.get("pause", 0.3) * SR), np.float32)]
    cur += len(audio) / SR + p.get("pause", 0.3)
    print(p["id"], f"{len(audio)/SR:.2f}s", flush=True)
tail = 1.6
out = np.concatenate(chunks + [np.zeros(int(tail * SR), np.float32)])
w = wave.open(f"{out_dir}/voice.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes()); w.close()
json.dump({"phrases": phrases, "duration": round(cur + tail, 3)}, open(f"{out_dir}/timing.json", "w"))
print("duration", round(cur + tail, 2))
