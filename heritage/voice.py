"""Synthesize the French voice-over with Kokoro (open source, voice ff_siwis), phrase by phrase.
Writes out/voice.wav and out/timing.json ({anchors: [[old_anchor, new_start], ...], duration}).
Usage: python3 voice.py /path/to/kokoro-v1.0.int8.onnx /path/to/voices-v1.0.bin
(model files: github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0)"""
import sys, json, wave, numpy as np
from kokoro_onnx import Kokoro
# (anchor time in the original 34 s timeline, text, pause after in s)
SCRIPT = [
    (0.00, "Sois honnête.", 0.25),
    (0.50, "Tu veux te lancer en ligne…", 0.15),
    (1.70, "mais tu ne sais pas par où commencer ?", 0.5),
    (4.70, "Tu te dis : je pars de zéro.", 0.2),
    (5.20, "Encore une formation ?", 0.2),
    (5.65, "Et si je perds mon temps ?", 0.3),
    (6.25, "Tu doutes. Et c'est normal.", 0.3),
    (7.60, "Mais surtout : ça se travaille.", 0.5),
    (9.30, "Ce n'est pas l'ambition qui te manque.", 0.3),
    (11.15, "C'est une méthode.", 0.55),
    (13.10, "Ce qu'il te faut ?", 0.3),
    (14.00, "Une méthode claire, étape par étape.", 0.3),
    (15.20, "Un cadre, pour rester régulier.", 0.3),
    (16.40, "Des coachings et une communauté, pour ne plus avancer seul.", 0.35),
    (17.50, "C'est toute l'idée d'Héritage.", 0.55),
    (19.25, "Héritage, par I. H. C.", 0.45),
    (21.05, "Fondation : tu avances en autonomie, à ton rythme.", 0.25),
    (21.65, "Bildeur : tu ajoutes un coaching collectif chaque semaine.", 0.25),
    (22.25, "Éternelle : deux coachings par semaine, et un groupe privé.", 0.55),
    (24.85, "Ne cherche pas un raccourci.", 0.35),
    (26.45, "Construis quelque chose qui dure. Pour toi, et pour ta famille.", 0.55),
    (28.65, "Le lien est dans ma bio.", 0.3),
    (29.35, "Découvre le programme.", 0.2),
    (30.15, "Lis le prix et les conditions avant de te décider.", 0.3),
    (30.95, "Puis choisis… sans pression.", 0.0),
]
tts = Kokoro(sys.argv[1], sys.argv[2])
SPEED = 1.12  # dynamic but still clear
sr = 24000
chunks, anchors, cur = [], [], 0.25
chunks.append(np.zeros(int(0.25 * sr), np.float32))
for old, text, pause in SCRIPT:
    audio, sr = tts.create(text, voice='ff_siwis', speed=SPEED, lang='fr-fr')
    pause *= 0.8
    # trim leading/trailing silence so anchors land on the first syllable
    nz = np.where(np.abs(audio) > 0.02)[0]
    audio = audio[max(0, nz[0] - 200): nz[-1] + 800]
    anchors.append([old, round(cur, 3)])
    chunks += [audio, np.zeros(int(pause * sr), np.float32)]
    cur += len(audio) / sr + pause
end = cur + 2.6
anchors.append([34.0, round(end, 3)])
out = np.concatenate(chunks + [np.zeros(int(2.6 * sr), np.float32)])
w = wave.open('out/voice.wav', 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((np.clip(out, -1, 1) * 32767).astype('<i2').tobytes()); w.close()
json.dump({'anchors': anchors, 'duration': round(end, 3)}, open('out/timing.json', 'w'))
print(json.dumps(anchors), end)
