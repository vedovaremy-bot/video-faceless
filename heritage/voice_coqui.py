"""Free male French voice-over (Coqui TTS, model tts_models/fr/css10/vits), phrase by phrase.
Usage: python3 voice_coqui.py <scripts/vX.js> <outDir> <model_dir>
Writes <outDir>/voice.wav + <outDir>/timing.json in the same format as voice_el.py.
Word times: silent gaps in each phrase are matched to its punctuation; words in between are spread by length."""
import sys, json, re, wave
import numpy as np
from TTS.api import TTS

script_file, out_dir, model_dir = sys.argv[1:4]
src = open(script_file, encoding="utf-8").read()
SCRIPT = json.loads(src[src.index("["):src.rindex("]") + 1])
# spelling fixes so the grapheme model pronounces English/abbreviations right (display text is untouched)
SAY = [(r"\bDM\b", "dé èm"), (r"\b[Ll]ike\b", "laïk"), (r"coachings", "cotchinngues"), (r"TikTok", "tic toc"),
       (r"YouTube", "you tioube"), (r"…", "..."), (r"[«»]", ""), (r"HÉRITAGE", "Héritage"), (r"t'as", "tu as"), (r"t'es", "tu es")]
def spoken(s):
    for a, b in SAY: s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()

tts = TTS(model_path=f"{model_dir}/model_file.pth.tar", config_path=f"{model_dir}/config.json", progress_bar=False)
tts.synthesizer.tts_model.length_scale = 0.88   # a bit faster = more energy
SR = tts.synthesizer.output_sample_rate

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
    a = np.array(tts.tts(spoken(p["text"])), dtype=np.float32)
    nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, nz[0] - int(0.02 * SR)): nz[-1] + int(0.1 * SR)]
    a = a / max(1e-6, np.max(np.abs(a))) * 0.9
    toks = p["text"].split(); L = len(a) / SR
    weight = [max(1, len(re.sub(r"[^\wÀ-ÿ']", "", w))) + 1.5 for w in toks]
    for i, w in enumerate(toks):
        if re.fullmatch(r"[«»:]", w): weight[i] = 0.01
    # segment boundaries after punctuated words, matched to the longest internal gaps
    breaks = [i for i, w in enumerate(toks[:-1]) if re.search(r"[,.:?!…]$", w) and not re.fullmatch(r"[«»]", w)]
    g = sorted([x for x in gaps(a) if 0.15 < x[0] < L - 0.15], key=lambda x: x[0] - x[1])[:len(breaks)]
    g = sorted(g)
    bounds = [(0, 0.0)]
    if len(g) == len(breaks): bounds += [(b + 1, gg[1]) for b, gg in zip(breaks, g)]
    bounds.append((len(toks), L))
    times = [0.0] * len(toks)
    for (i0, t0), (i1, t1) in zip(bounds, bounds[1:]):
        seg = weight[i0:i1]; tot = sum(seg) or 1; acc = t0
        end_t = t1 if i1 == len(toks) else (next((gg[0] for b, gg in zip(breaks, g) if b + 1 == i1), t1))
        for k, wgt in enumerate(seg): times[i0 + k] = acc; acc += (end_t - t0) * wgt / tot
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
