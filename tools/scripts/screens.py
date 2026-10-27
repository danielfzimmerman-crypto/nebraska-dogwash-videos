# screens.py IN.mp4 OUT.mp4 [--still]  — fill the blanked blue station screens with the lookalike menu art
# (screen_main.png landscape, screen_side.png portrait). Keys the blue per frame, so dogs/foam in front stay in front.
import sys, subprocess, json, os
import numpy as np, cv2
IN, OUT = sys.argv[1], sys.argv[2]
ART = os.environ.get('SCREEN_ART', os.path.dirname(os.path.abspath(__file__)) + '/../specs/')
MAIN = cv2.imread(ART + 'screen_main.png'); SIDE = cv2.imread(ART + 'screen_side.png')

def blue_mask(f):
    h = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    return ((h[..., 0] > 98) & (h[..., 0] < 128) & (h[..., 1] > 120) & (h[..., 2] > 110)).astype(np.uint8)

def order(p):
    p = np.array(p, np.float32).reshape(-1, 2); s = p.sum(1); d = np.diff(p, axis=1).ravel()
    return np.array([p[np.argmin(s)], p[np.argmin(d)], p[np.argmax(s)], p[np.argmax(d)]], np.float32)

def quads(f):
    H, W = f.shape[:2]
    m = cv2.morphologyEx(blue_mask(f), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, l, st, c = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < 2500 or a / (w * h) < .62 or c[i][1] > H * .62: continue
        cs, _ = cv2.findContours((l == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hull = cv2.convexHull(max(cs, key=cv2.contourArea)); per = cv2.arcLength(hull, True); q = None
        for e in (.01, .02, .03, .04, .06):
            ap = cv2.approxPolyDP(hull, e * per, True)
            if len(ap) == 4: q = order(ap); break
        if q is None: q = order(cv2.boxPoints(cv2.minAreaRect(hull)))
        out.append(dict(q=q, c=np.array(c[i]), a=float(a), bb=(int(x), int(y), int(w), int(h))))
    return out

def extend(q, bb, W, H, aspect):
    q = q.copy(); x, y, w, h = bb
    hgt = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
    want = hgt * aspect
    cur = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
    if cur >= want * .97: return q
    if x <= 1:   # clipped on the left: push TL/BL outward
        for a_, b_ in ((0, 1), (3, 2)): v = q[a_] - q[b_]; q[a_] = q[b_] + v / np.linalg.norm(v) * want
    elif x + w >= W - 1:
        for a_, b_ in ((1, 0), (2, 3)): v = q[a_] - q[b_]; q[a_] = q[b_] + v / np.linalg.norm(v) * want
    return q

def probe(p):
    o = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                                   '-of', 'json', p], capture_output=True).stdout)['streams'][0]
    return o['width'], o['height'], o['r_frame_rate']

W, H, R = probe(IN)
def frames():
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', IN, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
    while True:
        b = pr.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)

# pass 1: track screens
det = [quads(f) for f in frames()]
tracks = [[d] for d in det[0]]
for fd in det[1:]:
    for t in tracks:
        last = t[-1]; best = min(fd, key=lambda d: np.linalg.norm(d['c'] - last['c']), default=None)
        t.append(best if best is not None and np.linalg.norm(best['c'] - last['c']) < 60 else last)
plans = []
for t in tracks:
    cs = np.array([d['c'] for d in t]); static = cs.std(0).max() < 4
    asp = lambda d: np.linalg.norm(d['q'][1] - d['q'][0]) / max(1, np.linalg.norm(d['q'][3] - d['q'][0]))
    ref = max(t, key=lambda d: d['a'])
    kind = 'main' if asp(ref) > 1.05 else 'side'
    if len(tracks) >= 2:   # both station models: big screen on the left, menu screen on the right
        xs = sorted(np.mean([d['c'][0] for d in tt]) for tt in tracks)
        mx = np.mean(cs[:, 0]); kind = 'main' if mx == xs[0] else ('side' if mx == xs[-1] else kind)
    aspect = 16 / 9 if kind == 'main' else .6
    if static:
        q = extend(ref['q'], ref['bb'], W, H, aspect); qs = [q] * len(t)
    else:
        raw = np.array([extend(d['q'], d['bb'], W, H, aspect) for d in t])
        qs = [np.median(raw[max(0, i - 5):i + 6], 0) for i in range(len(raw))]
    plans.append((kind, qs))
print(IN, [(k, 'n=%d' % len(q)) for k, q in plans])

# pass 2: composite
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', R, '-i', '-',
                        '-i', IN, '-map', '0:v', '-map', '1:a?', '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy', OUT], stdin=subprocess.PIPE)
for i, f in enumerate(frames()):
    f = f.astype(np.float32)
    hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    key = (np.clip((hsv[..., 1] - 90) / 60, 0, 1) * np.clip((hsv[..., 2] - 80) / 60, 0, 1) *
           np.clip(1 - np.abs(hsv[..., 0] - 113) / 18, 0, 1) * 1.6).clip(0, 1)
    for kind, qs in plans:
        q = qs[min(i, len(qs) - 1)]; art = MAIN if kind == 'main' else SIDE
        src = np.float32([[0, 0], [art.shape[1], 0], [art.shape[1], art.shape[0]], [0, art.shape[0]]])
        M = cv2.getPerspectiveTransform(src, q)
        warped = cv2.warpPerspective(art, M, (W, H), flags=cv2.INTER_AREA).astype(np.float32)
        warped = cv2.GaussianBlur(warped, (3, 3), 0) * .93
        poly = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(poly, q.astype(np.int32), 1)
        poly = cv2.dilate(poly, np.ones((5, 5), np.uint8))
        a = (key * poly)[..., None]
        f = f * (1 - a) + warped * a
    enc.stdin.write(f.clip(0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait(); print('done', OUT)
