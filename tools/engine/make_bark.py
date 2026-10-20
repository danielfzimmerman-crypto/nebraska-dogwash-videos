"""make_bark.py SRC.mp4 OUT.wav [i,j]  -> 1.15 s track with two barks starting at .10 s and .65 s
Finds bark onsets in the Veo clip's audio; uses barks i and j (default first two)."""
import sys, subprocess, numpy as np, wave
SR = 48000
src, out = sys.argv[1], sys.argv[2]
pick = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0, 1]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout
x = np.frombuffer(raw, np.int16).astype(float) / 32768
w = int(.01 * SR)
e = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, w)])
floor = np.percentile(e, 30); peak = e.max(); th = floor + .25 * (peak - floor)
on = []; i = 0
while i < len(e):
    if e[i] > th:
        j = i
        while j < len(e) and e[j] > floor + .08 * (peak - floor): j += 1
        on.append((i, j, e[i:j].max())); i = j + 5
    else: i += 1
print('barks (start s, end s, level):', [(round(a * .01, 2), round(b * .01, 2), round(m, 3)) for a, b, m in on])
L = int(1.15 * SR); trk = np.zeros(L)
for slot, k in zip((.10, .65), pick):
    a, b, m = on[k]
    s0 = max(0, a * w - int(.015 * SR)); seg = x[s0:min(len(x), b * w + int(.04 * SR))]
    seg = seg[:int(.5 * SR)]
    n = len(seg); fade = np.minimum(1, np.arange(n) / (.004 * SR)) * np.minimum(1, (n - np.arange(n)) / (.03 * SR))
    seg = seg * fade / (np.abs(seg).max() + 1e-9)
    p = int(slot * SR); trk[p:p + n] += seg[:L - p]
trk = trk / (np.abs(trk).max() + 1e-9) * .95
with wave.open(out, 'wb') as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((trk * 32000).astype(np.int16).tobytes())
print('wrote', out)
