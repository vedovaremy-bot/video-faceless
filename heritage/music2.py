"""Original soundtrack + sound design synced to <outDir>/events.json -> <outDir>/music.wav
Usage: python3 music2.py <outDir> <duration> [seed]
Dark/warm chords + a soft driving pulse (keeps momentum), impacts on slams, pops, checks, like/sub dings."""
import sys, json, wave, numpy as np
out_dir, DUR = sys.argv[1], float(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
SR = 44100; n = int(SR * DUR); t = np.arange(n) / SR
rng = np.random.default_rng(seed); out = np.zeros(n)
note = lambda m: 440 * 2 ** ((m - 69) / 12)
progs = [[[57, 64, 67, 72], [53, 60, 64, 69], [48, 55, 64, 67], [55, 62, 67, 71]],
         [[50, 57, 62, 65], [46, 53, 58, 62], [53, 60, 65, 69], [48, 55, 60, 64]],
         [[52, 59, 64, 67], [48, 55, 60, 64], [55, 62, 67, 71], [50, 57, 62, 66]]]
chords = progs[seed % 3]
BPM = 96; beat = 60 / BPM; bar = beat * 4
def add(at, sig, amp=1.0):
    a = int(at * SR)
    if a >= n or a + len(sig) <= 0: return
    s0 = max(0, -a); a = max(0, a); b = min(n, a + len(sig) - s0); out[a:b] += amp * sig[s0:s0 + b - a]
# pads
for i in range(int(np.ceil(DUR / bar)) + 1):
    s0 = i * bar; ch = chords[i % 4]; L = int((bar + 1.2) * SR); tt = np.arange(L) / SR
    env = np.clip(tt / 0.8, 0, 1) * np.clip((bar + 1.2 - tt) / 1.2, 0, 1)
    sig = sum(0.02 * np.sin(2 * np.pi * note(m) * (1 + d / 100) * tt + rng.uniform(0, 6)) for m in ch for d in (-0.1, 0.1))
    sig += 0.06 * np.sin(2 * np.pi * note(ch[0] - 12) * tt)
    add(s0, sig * env)
# pulse: soft kick on beats, shaker on off-beats (starts after the hook's first second)
L = int(0.35 * SR); tt = np.arange(L) / SR
kick = np.sin(2 * np.pi * (48 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
sh = rng.standard_normal(int(0.06 * SR)) * np.exp(-np.arange(int(0.06 * SR)) / SR * 70)
sh = np.diff(np.concatenate([[0], sh]))
k = 0
while k * beat < DUR - 1.5:
    at = 0.9 + k * beat
    add(at, kick, 0.22); add(at + beat / 2, sh, 0.05)
    k += 1
# sfx
def tone(f, dur, decay, amp, sweep=0.0):
    L = int(dur * SR); tt = np.arange(L) / SR
    return amp * np.exp(-tt * decay) * np.sin(2 * np.pi * f * tt * (1 + sweep * np.exp(-tt * 40)))
def noise(dur, smooth, amp):
    L = int(dur * SR); x = np.convolve(rng.standard_normal(L), np.ones(smooth) / smooth, 'same'); tt = np.arange(L) / SR
    return amp * x * np.sin(np.pi * tt / dur) ** 2
for e in json.load(open(f"{out_dir}/events.json")):
    k, at = e["kind"], e["t"]
    if at < -0.05: continue
    if k == "whoosh": add(at - 0.3, noise(0.6, 40, 0.25))
    elif k == "hit":
        add(at, tone(55, 0.6, 7, 0.55)); add(at, noise(0.18, 4, 0.3))
    elif k == "pop": add(at, tone(990, 0.15, 35, 0.12, 0.5))
    elif k == "check": add(at, tone(1320, 0.2, 25, 0.1)); add(at + 0.07, tone(1760, 0.25, 20, 0.08))
    elif k == "like": add(at, tone(880, 0.3, 14, 0.12)); add(at + 0.08, tone(1320, 0.4, 10, 0.1))
    elif k == "ding": add(at, tone(1568, 0.6, 6, 0.1)); add(at, tone(2093, 0.6, 7, 0.06))
    elif k == "type":
        for j in range(int(e.get("d", 0.6) / 0.08)): add(at + j * 0.08, noise(0.03, 2, 0.12))
fade = np.clip((DUR - t) / 1.5, 0, 1) * np.clip(t / 0.05, 0, 1)
out *= fade; out = out / np.max(np.abs(out)) * 0.85
st = np.stack([out, np.roll(out, 300) * 0.97], 1)
w = wave.open(f"{out_dir}/music.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype("<i2").tobytes()); w.close()
