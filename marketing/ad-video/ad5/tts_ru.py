"""Russian voice lines for ad 6 (C3) with Meta MMS (facebook/mms-tts-rus), CPU only; the same synthesized-voice route the
owner accepted for the Uzbek cut on 2026-11-19. Needs: pip install torch (cpu) transformers; Hugging Face reachable.

Usage: python3 ad5/tts_ru.py <out dir>   -> ru-c3-02.mp3, ru-c3-03.mp3, ru-c3-04.mp3, ru-v07.mp3 (not committed)
"Yondo" is written «Йондо» for the speech model only; the captions keep the brand spelling.
"""
import subprocess
import sys

import numpy as np
import torch
from transformers import AutoTokenizer, VitsModel

LINES = [('ru-c3-02', 'Занятие: кофе, прогулка, кино, мероприятие.'), ('ru-c3-03', 'Компаньон: в профиле видно, что он предлагает.'),
         ('ru-c3-04', 'Встреча: открыто, в общественном месте.'), ('ru-v07', 'Йондо. Всегда рядом.')]
model, tok = VitsModel.from_pretrained('facebook/mms-tts-rus'), AutoTokenizer.from_pretrained('facebook/mms-tts-rus')
for name, text in LINES:
    torch.manual_seed(1)                       # the model samples durations: a fixed seed gives the same file every run
    with torch.no_grad():
        wave = model(**tok(text.lower(), return_tensors='pt')).waveform[0].numpy()
    sr = model.config.sampling_rate
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-', '-c:a', 'libmp3lame',
                    '-q:a', '2', f'{sys.argv[1]}/{name}.mp3'], input=wave.astype(np.float32).tobytes(), check=True)
    print(name, round(len(wave) / sr, 2), 's')
