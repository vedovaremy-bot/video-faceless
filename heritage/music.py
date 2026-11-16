"""Original ambient soundtrack + sound design synced to out/events.json -> out/audio.wav"""
import json, wave, numpy as np
SR, DUR = 44100, 34.0
n = int(SR * DUR); t = np.arange(n) / SR
rng = np.random.default_rng(7)
out = np.zeros(n)

def note(f): return 440 * 2 ** ((f - 69) / 12)
# Slow, warm progression (Am9 - Fmaj7 - C - G6), 4.25s per chord, looped
chords = [[57, 64, 67, 71, 74], [53, 60, 64, 69, 72], [48, 55, 64, 67, 71], [55, 62, 67, 71, 76]]
seg = 4.25
for i in range(int(np.ceil(DUR / seg))):
    s0 = i * seg; ch = chords[i % 4]
    a, b = int(s0 * SR), min(n, int((s0 + seg + 1.5) * SR))
    tt = t[a:b] - s0
    env = np.clip(tt / 1.2, 0, 1) * np.clip((seg + 1.5 - tt) / 1.5, 0, 1)
    for m in ch:
        f = note(m)
        for det in (-0.12, 0.12):
            out[a:b] += 0.022 * env * np.sin(2 * np.pi * f * (1 + det / 100) * tt + rng.uniform(0, 6))
    # soft bass
    out[a:b] += 0.05 * env * np.sin(2 * np.pi * note(ch[0] - 12) * tt)
# gentle arpeggio pluck (8th notes) from 4.2s on
step = seg / 8
for k in range(int(4.2 / step), int((DUR - 1.5) / step)):
    s0 = k * step; ch = chords[int(s0 // seg) % 4]
    m = ch[[0, 2, 4, 3, 1, 3, 4, 2][k % 8]] + 12
    a = int(s0 * SR); L = int(0.9 * SR); b = min(n, a + L); tt = t[a:b] - s0
    out[a:b] += 0.03 * np.exp(-tt * 5) * np.sin(2 * np.pi * note(m) * tt) * (1 + 0.3 * np.sin(2 * np.pi * 2 * note(m) * tt))

def add(at, sig):
    a = int(at * SR); b = min(n, a + len(sig)); out[a:b] += sig[:b - a]
def whoosh():
    L = int(0.6 * SR); x = rng.standard_normal(L); x = np.convolve(x, np.ones(40) / 40, 'same')
    tt = np.arange(L) / SR; return 0.25 * x * np.sin(np.pi * tt / 0.6) ** 2
def pop(f=880, amp=0.12):
    L = int(0.15 * SR); tt = np.arange(L) / SR
    return amp * np.exp(-tt * 35) * np.sin(2 * np.pi * f * tt * (1 + 0.5 * np.exp(-tt * 60)))

for e in json.load(open('out/events.json')):
    k, at = e['kind'], e['t']
    if k == 'whoosh' and at > 0: add(at - 0.3, whoosh())
    elif k == 'pop': add(at, pop(990))
    elif k == 'check': add(at, pop(1320, 0.1))
    elif k == 'strike': add(at, whoosh()[:int(0.3 * SR)] * 0.8)
    elif k == 'word': add(at, pop(1800, 0.018))

fade = np.clip((DUR - t) / 2.0, 0, 1) * np.clip(t / 0.3, 0, 1)
out *= fade
out = out / np.max(np.abs(out)) * 0.85
st = np.stack([out, np.roll(out, 300) * 0.97], 1)  # light stereo width
w = wave.open('out/audio.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype('<i2').tobytes()); w.close()
