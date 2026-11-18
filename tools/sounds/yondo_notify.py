"""Yondo notification sounds: original synthesis (no samples). Struck metal bowl / water gong with a droplet onset.
Usage: python yondo_notify.py <out_dir>. Deterministic (fixed seed)."""
import sys, wave, os
import numpy as np

SR = 48000
rng = np.random.default_rng(2026)


def glide(t, rise=0.05, tau1=0.016, drift=0.004, tau2=0.5):
    # liquid onset: pitch starts a little low and snaps up (droplet), then sinks slowly (gong lowered into water)
    return (1 - rise * np.exp(-t / tau1)) * (1 - drift * (1 - np.exp(-t / tau2)))


def band_noise(n, lo, hi):
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-0.5 * ((np.log(np.maximum(f, 1)) - np.log(np.sqrt(lo * hi))) / (np.log(hi / lo) / 2.5)) ** 2)
    y = np.fft.irfft(X, n)
    return y / (np.max(np.abs(y)) + 1e-9)


def strike(dur, f0, partials, g=None, width=0.6, tick=0.06, decay_scale=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    L = np.zeros(n)
    R = np.zeros(n)
    base = 2 * np.pi * np.cumsum(glide(t, **(g or {}))) / SR
    for ratio, amp, t60, beat in partials:
        f = f0 * ratio
        if f > SR * 0.42:
            continue
        e = amp * np.exp(-6.908 * t / (t60 * decay_scale))
        p = rng.uniform(0, 2 * np.pi)
        a = np.sin(f * base + np.pi * beat * t + p)
        b = np.sin(f * base - np.pi * beat * t + 0.7 * p)
        L += e * (a * (0.5 + width / 2) + b * (0.5 - width / 2))
        R += e * (a * (0.5 - width / 2) + b * (0.5 + width / 2))
    att = int(0.004 * SR)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(att) / att)
    L[:att] *= ramp
    R[:att] *= ramp
    m = int(0.014 * SR)  # soft mallet contact
    tk = band_noise(m, 1500, 6000) * np.exp(-np.arange(m) / (0.0022 * SR)) * tick
    L[:m] += tk
    R[:m] += tk
    return np.stack([L, R])


def droplet(f_a, f_b, dur=0.085, tau=0.020):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f_a + (f_b - f_a) * (t / dur) ** 0.55
    ph = 2 * np.pi * np.cumsum(f) / SR
    e = np.exp(-t / tau) * np.minimum(1, t / 0.0015)
    x = np.sin(ph) * e
    return np.stack([x, x])


def reverb(x, wet=0.12, t60=1.1, predelay=0.012):
    m = int((t60 + 0.2) * SR)
    t = np.arange(m) / SR
    ir = np.stack([band_noise(m, 300, 5000), band_noise(m, 300, 5000)]) * np.exp(-6.908 * t / t60)
    ir /= np.sqrt(np.sum(ir ** 2, axis=1, keepdims=True))
    n = x.shape[1] + m + int(predelay * SR)
    size = 1 << (n - 1).bit_length()
    out = np.zeros((2, n))
    for c in range(2):
        y = np.fft.irfft(np.fft.rfft(x[c], size) * np.fft.rfft(ir[c], size), size)[: x.shape[1] + m]
        out[c, int(predelay * SR): int(predelay * SR) + len(y)] += y * wet
        out[c, : x.shape[1]] += x[c]
    return out


def mix(total, events):
    buf = np.zeros((2, int(total * SR)))
    for at, gain, sig in events:
        i = int(at * SR)
        k = min(sig.shape[1], buf.shape[1] - i)
        buf[:, i: i + k] += gain * sig[:, :k]
    return buf


def finish(x, total, peak=0.84, fade=0.18):
    x = x[:, : int(total * SR)]
    x = x - x.mean(axis=1, keepdims=True)
    n = int(fade * SR)
    x[:, -n:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(n) / n)
    return x * (peak / np.max(np.abs(x)))


# (ratio, amplitude, T60 seconds, beat Hz). Ratios 2.76 / 5.40 / 8.93 = a struck bowl/bar; 0.5 = the bell's hum tone.
RIN = [(0.5, 0.10, 1.5, 0.5), (1.0, 1.0, 2.1, 0.9), (2.76, 0.40, 1.1, 1.6), (5.40, 0.13, 0.5, 2.3), (8.93, 0.04, 0.22, 3.1)]
GONG = [(1.0, 1.0, 3.0, 0.7), (1.48, 0.34, 2.1, 1.1), (2.0, 0.60, 2.4, 0.9), (2.76, 0.42, 1.7, 1.7),
        (3.52, 0.22, 1.2, 2.2), (4.07, 0.26, 1.0, 1.4), (5.40, 0.15, 0.7, 2.6), (6.80, 0.07, 0.45, 3.0)]


def variant_a():  # one bright bowl: droplet -> ding with a long shimmer
    ev = [(0.000, 0.20, droplet(900, 2600)),
          (0.035, 1.00, strike(2.3, 1046.50, RIN))]
    return finish(reverb(mix(2.4, ev), wet=0.12, t60=1.0), 2.4)


def variant_b():  # two bowls a fifth apart (G5 -> D6): "da-ding", confirmation feel
    ev = [(0.000, 0.16, droplet(800, 2200)),
          (0.030, 0.62, strike(1.4, 783.99, RIN, decay_scale=0.55)),
          (0.200, 1.00, strike(2.3, 1174.66, RIN))]
    return finish(reverb(mix(2.6, ev), wet=0.12, t60=1.0), 2.6)


def variant_c():  # deep water gong: big metal, pitch sinks like a gong lowered into water, drips on top
    g = dict(rise=0.03, tau1=0.03, drift=0.018, tau2=0.7)
    ev = [(0.000, 0.22, droplet(700, 1900)),
          (0.030, 1.00, strike(3.0, 293.66, GONG, g=g, width=0.8, tick=0.04)),
          (0.450, 0.09, droplet(900, 2400)),
          (0.450, 0.10, strike(1.2, 1174.66, RIN, decay_scale=0.5, tick=0.0))]
    return finish(reverb(mix(3.2, ev), wet=0.16, t60=1.4), 3.2)


def save(path, x):
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def report(name, x):
    mono = x.mean(axis=0)
    peak = 20 * np.log10(np.max(np.abs(x)))
    rms = 20 * np.log10(np.sqrt(np.mean(mono ** 2)))
    w = int(0.02 * SR)
    env = np.sqrt(np.convolve(mono ** 2, np.ones(w) / w, "same"))
    env_db = 20 * np.log10(env / env.max() + 1e-12)
    below = np.where(env_db > -40)[0]
    S = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    idx = [i for i in range(2, len(S) - 2) if S[i] > S[i - 1] and S[i] > S[i + 1] and S[i] > 0.05 * S.max()]
    top = sorted(idx, key=lambda i: -S[i])[:6]
    cent = float(np.sum(f * S) / np.sum(S))
    print(f"{name}: dur={x.shape[1]/SR:.2f}s peak={peak:.1f}dBFS rms={rms:.1f}dBFS clipped={(np.abs(x)>=0.999).sum()} "
          f"audible_until(-40dB)={below[-1]/SR:.2f}s centroid={cent:.0f}Hz peaks={[int(round(f[i])) for i in sorted(top)]} "
          f"first/last sample={x[0,0]:.4f}/{x[0,-1]:.5f}")


if __name__ == "__main__":
    out = sys.argv[1]
    for name, fn in [("yondo-bildirishnoma-A-tomchi-rin", variant_a), ("yondo-bildirishnoma-B-ikki-jarang", variant_b),
                     ("yondo-bildirishnoma-C-suv-gongi", variant_c)]:
        x = fn()
        save(os.path.join(out, name + ".wav"), x)
        report(name, x)
