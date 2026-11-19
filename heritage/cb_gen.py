"""Chatterbox (open source, MIT) phrase generator — runs inside the Chatterbox venv, called by voice_cb.py.
Usage: <venv>/bin/python cb_gen.py <jobs.json> <reference.wav>
jobs.json = [{"id": "p1", "text": "...", "out": "/path/p1.wav"}, ...]
The reference must be a voice the owner has the right to use (here: the owner's own recording)."""
import sys, json, torch, torchaudio as ta
_load = torch.load
torch.load = lambda *a, **k: _load(*a, **{**k, "map_location": torch.device("cpu")})  # CPU-only machine
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

jobs, ref = json.load(open(sys.argv[1])), sys.argv[2]
m = ChatterboxMultilingualTTS.from_pretrained(device=torch.device("cpu"))
for j in jobs:
    torch.manual_seed(7)
    wav = m.generate(j["text"], language_id="fr", audio_prompt_path=ref,
                     exaggeration=j.get("exaggeration", 0.6), cfg_weight=j.get("cfg", 0.4))
    ta.save(j["out"], wav, m.sr)
    print(j["id"], round(wav.shape[-1] / m.sr, 2), "s", flush=True)
