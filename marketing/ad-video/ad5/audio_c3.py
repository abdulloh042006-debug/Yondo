"""Sound for ad 6 «Yondo nima?» (C3): original synthesis (pad + light kick + SFX), optional voice with ducking.

Usage: python3 ad5/audio_c3.py <out.wav> [voice_dir]
voice_dir holds c3-02.mp3, c3-03.mp3, c3-04.mp3, v07.mp3 (the DRAFT MMS voice or the owner's voicelab.uz take with the same
names). Without voice_dir the mix is music + SFX only. Output: 48 kHz stereo WAV, not normalised (mux does loudnorm).
"""
import subprocess
import sys

import numpy as np

SR, DUR = 48000, 13.3
N = int(SR * DUR)
rng = np.random.default_rng(7)          # fixed seed: the same file every run
t_all = np.arange(N) / SR


def env(n, a, r):
    e = np.ones(n)
    ai, ri = int(a * SR), int(r * SR)
    e[:ai] = np.linspace(0, 1, ai)
    e[-ri:] *= np.linspace(1, 0, ri)
    return e


def add(buf, sig, at, gain=1.0):
    i = max(0, int(at * SR))
    if i >= N:
        return
    j = min(N, i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def tone(freqs, dur, a=.02, r=.3, kind='sine'):
    t = np.arange(int(dur * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * t) + (.3 * np.sin(4 * np.pi * f * t) if kind == 'warm' else 0) for f in freqs)
    return s / len(freqs) * env(len(t), a, r)


def noise(dur, lo=0.0, hi=1.0):
    x = rng.standard_normal(int(dur * SR))
    f = np.fft.rfft(x)
    k = np.fft.rfftfreq(len(x), 1 / SR) / (SR / 2)
    f[(k < lo) | (k > hi)] = 0
    return np.fft.irfft(f, len(x))


music = np.zeros(N)
sfx = np.zeros(N)
# pad: D - A - Bm - G (Hz of the chord tones), 100 BPM -> one chord per 2.4 s
chords = [[146.8, 185.0, 220.0], [110.0, 138.6, 164.8], [123.5, 146.8, 185.0], [98.0, 123.5, 146.8]]
for i, c in enumerate(chords * 2):
    add(music, tone([f * 2 for f in c], 2.6, a=.4, r=.8, kind='warm'), 1.4 + i * 2.4, .22)
# light kick on the beat from 1.4 s, stopping under the end card's quiet logo build
beat = 60 / 100
for b in np.arange(1.4, 11.2, beat):
    tk = np.arange(int(.18 * SR)) / SR
    add(music, np.sin(2 * np.pi * (55 + 90 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 18), b, .5)
# SFX
def hit(at, g=.9):
    tk = np.arange(int(.9 * SR)) / SR
    add(sfx, np.sin(2 * np.pi * (45 + 60 * np.exp(-tk * 12)) * tk) * np.exp(-tk * 4), at, g)
def whoosh(at, d=.45, g=.35):
    s = noise(d, .02, .25) * np.hanning(int(d * SR))
    add(sfx, s / np.abs(s).max(), at - d / 2, g)
def pop(at, f=880, g=.35):
    add(sfx, tone([f, f * 1.5], .12, a=.002, r=.1), at, g)
def chime(at, g=.3):
    add(sfx, tone([1318.5, 1760.0, 2637.0], 1.4, a=.003, r=1.3), at, g)
hit(0.0, .6)
for w in (1.0, 4.2, 8.0, 10.3):
    whoosh(w)
for i, at in enumerate((1.9, 2.4, 2.9, 3.4)):
    pop(at, 660 * 2 ** (i / 6))
pop(5.6, 990, .3)
chime(10.3)
hit(11.2, .8)
chime(12.1, .22)

voice = np.zeros(N)
if len(sys.argv) > 2:
    for name, at in (('c3-02', 1.45), ('c3-03', 4.25), ('c3-04', 8.05), ('v07', 10.4)):
        raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', f'{sys.argv[2]}/{name}.mp3', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                             capture_output=True, check=True).stdout
        v = np.frombuffer(raw, dtype=np.float32).astype(float)
        add(voice, v / (np.abs(v).max() + 1e-9) * .9, at)
# duck music 8 dB while the voice speaks (smoothed envelope)
speaking = np.convolve((np.abs(voice) > .02).astype(float), np.ones(int(.25 * SR)) / int(.25 * SR), 'same') > 0
duck = np.convolve(np.where(speaking, 10 ** (-8 / 20), 1.0), np.ones(int(.12 * SR)) / int(.12 * SR), 'same')
mix = music * duck + sfx + voice
mix *= env(N, .005, .6)
mix /= np.abs(mix).max() / .7
st = np.stack([mix, mix], 1).astype(np.float32)
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s24le', sys.argv[1]],
               input=st.tobytes(), check=True)
print('wrote', sys.argv[1], 'voice' if len(sys.argv) > 2 else 'no voice')
