# mats.py IN.mp4 OUT.mp4 'POLY_JSON' [pitch_px]  — lay the black perforated rubber mats over bare floor
# POLY: floor polygon in pixels. Only floor-coloured (low-saturation, speckled, light) pixels inside it are
# replaced, so legs, shoes and the station stay in front. Perspective: holes shrink toward the top of the polygon.
import sys, json, subprocess
import numpy as np, cv2
IN, OUT, POLY = sys.argv[1], sys.argv[2], np.array(json.loads(sys.argv[3]), np.int32)
P0 = float(sys.argv[4]) if len(sys.argv) > 4 else 30.
o = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate',
                               '-of', 'json', IN], capture_output=True).stdout)['streams'][0]
W, H, R = o['width'], o['height'], o['r_frame_rate']
y0 = POLY[:, 1].min(); y1 = H
# perspective mat texture in screen space
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
t = np.clip((yy - y0) / max(1, y1 - y0), 0, 1); sc = .55 + .45 * t           # scale 0.55 at far edge, 1 at bottom
v = np.cumsum(1 / sc[:, :1], 0) * 1.8; v = np.repeat(v, W, 1)               # foreshortened depth coordinate
u = (xx - W * .55) / sc
P = P0
fu = (u / P) % 1; fv = (v / P + .5 * (np.floor(u / P) % 2)) % 1               # staggered holes
d = np.sqrt(((fu - .5) * 1.0) ** 2 + ((fv - .5) * 1.0) ** 2)
hole = np.clip((.2 - d) / .05, 0, 1)
seam = (np.abs(((u / (P * 19)) % 1) - .5) > .49).astype(np.float32)          # gap between mats
base = np.full((H, W), 30., np.float32)
rim = np.clip(1 - np.abs(d - .2) / .05, 0, 1) * 14                            # slight raised rim highlight
noise = cv2.GaussianBlur(np.random.default_rng(3).normal(0, 6, (H, W)).astype(np.float32), (0, 0), 1.2)
tex = base + rim + noise
poly = np.zeros((H, W), np.float32); cv2.fillPoly(poly, [POLY], 1.); poly = cv2.GaussianBlur(poly, (0, 0), 2)

def frames():
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', IN, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
    while True:
        b = pr.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', R, '-i', '-',
                        '-i', IN, '-map', '0:v', '-map', '1:a?', '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy', OUT], stdin=subprocess.PIPE)
for f in frames():
    ff = f.astype(np.float32); hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lum_bl = cv2.GaussianBlur(g, (0, 0), 9)
    floor = np.clip((75 - hsv[..., 1]) / 25, 0, 1) * np.clip((hsv[..., 2] - 70) / 25, 0, 1) * np.clip((240 - hsv[..., 2]) / 12, 0, 1)
    floor = cv2.morphologyEx(floor, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    floor = cv2.GaussianBlur(cv2.morphologyEx(floor, cv2.MORPH_CLOSE, np.ones((17, 17), np.uint8)), (0, 0), 1.5)
    a = (floor * poly)[..., None]
    shade = (lum_bl / 170.).clip(.35, 1.2)[..., None]                         # keep shadows (legs, station)
    holecol = np.stack([g * .30 + 18] * 3, -1)                                     # floor speckle shows through holes
    mat = np.repeat(tex[..., None], 3, -1) * shade
    mat = mat * (1 - hole[..., None]) + holecol * hole[..., None]
    mat = mat * (1 - seam[..., None]) + ff * .45 * seam[..., None]
    out = ff * (1 - a) + mat * a
    enc.stdin.write(out.clip(0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait(); print('done', OUT)
