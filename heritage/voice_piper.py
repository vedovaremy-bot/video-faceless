"""Free male French voice-over with Piper (voice fr_FR-tom-medium), phrase by phrase.
Usage: python3 voice_piper.py <scripts/vX.js> <outDir> <model.onnx>
(model: huggingface.co/rhasspy/piper-voices, fr/fr_FR/tom/medium)
Writes <outDir>/voice.wav + <outDir>/timing.json in the same format as voice_el.py.
Word times: silent gaps in each phrase are matched to its punctuation; words in between are spread by length."""
import sys, json, re, wave
import numpy as np
from piper import PiperVoice, SynthesisConfig

script_file, out_dir, model_path = sys.argv[1:4]
src = open(script_file, encoding="utf-8").read()
SCRIPT = json.loads(src[src.index("["):src.rindex("]") + 1])
# spelling fixes so the grapheme model pronounces English/abbreviations right (display text is untouched)
SAY = [(r"\bDM\b", "dé-èm"), (r"\b[Ll]ike\b", "laïk"), (r"coachings", "cotchingues"), (r"TikTok", "Tik Tok"),
       (r"YouTube", "You Tioube"), (r"[«»]", ""), (r"HÉRITAGE", "Héritage")]
def spoken(s):
    for a, b in SAY: s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()

voice = PiperVoice.load(model_path)
SR = voice.config.sample_rate

def gaps(a, min_len=0.09, thr=0.012):
    env = np.convolve(np.abs(a), np.ones(int(0.02 * SR)) / int(0.02 * SR), "same")
    quiet = env < thr; out, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]: j += 1
            if (j - i) / SR >= min_len: out.append((i / SR, j / SR))
            i = j
        else: i += 1
    return out

chunks, phrases, cur = [np.zeros(int(0.1 * SR), np.float32)], {}, 0.1
for p in SCRIPT:
    cfg = SynthesisConfig(length_scale=p.get("ls", 0.9), noise_scale=0.7, noise_w_scale=0.8)  # hook phrase faster
    a = np.concatenate([c.audio_float_array for c in voice.synthesize(spoken(p.get("say", p["text"])), syn_config=cfg)])
    nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0] - int(0.02 * SR)): nz[-1] + int(0.1 * SR)]
    a = a / max(1e-6, np.max(np.abs(a))) * 0.9
    toks = p["text"].split(); L = len(a) / SR
    weight = [max(1, len(re.sub(r"[^\wÀ-ÿ']", "", w))) + 1.5 for w in toks]
    for i, w in enumerate(toks):
        if re.fullmatch(r"[«»:]", w): weight[i] = 0.01
    # word times: proportional by length, then snapped to real pauses found near each punctuation mark
    tot = sum(weight); cum = np.concatenate([[0], np.cumsum(weight)]) / tot * L
    times = list(cum[:-1])
    G = [g for g in gaps(a) if 0.1 < g[0] < L - 0.1]
    breaks = [i for i, w in enumerate(toks[:-1]) if re.search(r"[,.:?!…]$", w) and not re.fullmatch(r"[«»]", w)]
    anchors = [(0, 0.0)]
    for b in breaks:
        exp = cum[b + 1]
        cand = [g for g in G if abs(g[0] - exp) < 0.7 and g[1] > anchors[-1][1]]
        if cand:
            g = min(cand, key=lambda g: abs(g[0] - exp)); anchors.append((b + 1, g[1])); G.remove(g)
    anchors.append((len(toks), L))
    for (i0, t0), (i1, t1) in zip(anchors, anchors[1:]):
        seg = weight[i0:i1]; st = sum(seg) or 1; acc = t0
        for k, wgt in enumerate(seg): times[i0 + k] = acc; acc += (t1 - t0) * wgt / st
    words = [round(cur + x, 3) for x in times]
    phrases[p["id"]] = {"start": words[0], "end": round(cur + L, 3), "words": words}
    pause = p.get("pause", 0.3)
    chunks += [a, np.zeros(int(pause * SR), np.float32)]; cur += L + pause
    print(p["id"], f"{L:.2f}s", flush=True)
tail = 1.6
out = np.concatenate(chunks + [np.zeros(int(tail * SR), np.float32)])
w = wave.open(f"{out_dir}/voice.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes()); w.close()
json.dump({"phrases": phrases, "duration": round(cur + tail, 3)}, open(f"{out_dir}/timing.json", "w"))
print("duration", round(cur + tail, 2))
