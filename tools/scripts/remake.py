# remake.py SPEC.json OUT.mp4  — v4 "Runway" Reels for Nebraska Dogwash
# Builds a 12 s 1080x1920 Reel: Runway footage (one clip, a cut sequence, or a split screen)
# + brand typography (Poppins Black on red blocks), logo badge, url pill, a foam wipe,
# then the approved barking-logo end card (cut from an approved v3 Reel), with music.
import json, sys, math, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SPEC = json.load(open(sys.argv[1])); OUT = sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, '..', 'engine')
W, H, FPS = 1080, 1920, 30
MAIN = 8.15                       # footage + type; the end card fills the rest
WIPE0 = MAIN - .6
END = SPEC['endcard']             # 3.85 s clip with the approved bark ending
RED = (192, 34, 53); WHITE = (255, 255, 255)
F = lambda w, s: ImageFont.truetype(os.path.join(FONTS, f'Poppins-{w}.ttf'), s)

def clamp(x, a=0., b=1.): return max(a, min(b, x))
def eob(t, s=1.6): t -= 1; return t * t * ((s + 1) * t + s) + 1
def eoc(t): return 1 - (1 - t) ** 3

# ---------------- footage
def read_clip(path, start, dur, box):
    """frames of `path` from `start` for `dur` s, cover-scaled into box (w,h)"""
    bw, bh = box
    vf = f'fps={FPS},scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh}'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start), '-i', path, '-t', str(dur), '-vf', vf,
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, bh, bw, 3)
    need = int(round(dur * FPS))
    if len(fr) < need: fr = np.concatenate([fr, np.repeat(fr[-1:], need - len(fr), 0)])
    return fr[:need]

def footage():
    lay = SPEC.get('layout', 'seq')
    if lay == 'split':                                 # two clips side by side, divider bar
        a, b = SPEC['clips']
        A = read_clip(a['file'], a.get('start', 0), MAIN, (W // 2, H)); B = read_clip(b['file'], b.get('start', 0), MAIN, (W // 2, H))
        out = np.concatenate([A, B], 2); out[:, :, W // 2 - 6:W // 2 + 6] = WHITE
        return out
    seq = []
    for c in SPEC['clips']:
        seq.append(read_clip(c['file'], c.get('start', 0), c['dur'], (W, H)))
    out = np.concatenate(seq)
    need = int(MAIN * FPS)
    if len(out) < need: out = np.concatenate([out, np.repeat(out[-1:], need - len(out), 0)])
    return out[:need]

# ---------------- type sprites
def block_line(text, size, fg=WHITE, bg=RED, pad=(26, 10), radius=14):
    f = F(900, size); b = f.getbbox(text)
    w, h = b[2] - b[0] + pad[0] * 2, int(size * 1.08) + pad[1] * 2
    im = Image.new('RGBA', (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((12, 16, w + 12, h + 16), radius, fill=(0, 0, 0, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    if bg: d.rounded_rectangle((6, 6, w + 6, h + 6), radius, fill=bg + (255,))
    d.text((6 + pad[0] - b[0], 6 + pad[1] + (int(size * 1.08) - size) // 2 - b[1] + int(size * .06)), text, font=f, fill=fg + (255,))
    return im

def plain_line(text, size, fg=WHITE, weight=900, stroke=0):
    f = F(weight, size); b = f.getbbox(text, stroke_width=stroke)
    im = Image.new('RGBA', (b[2] - b[0] + 40, b[3] - b[1] + 40), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((22 - b[0], 26 - b[1]), text, font=f, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).text((20 - b[0], 20 - b[1]), text, font=f, fill=fg + (255,), stroke_width=stroke, stroke_fill=RED + (255,))
    return im

LOGO = Image.open(SPEC['logo']).convert('RGBA')
def logo_badge():
    lg = LOGO.crop(LOGO.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())
    lg = lg.resize((230, int(lg.height * 230 / lg.width)), Image.LANCZOS)
    im = Image.new('RGBA', (lg.width + 60, lg.height + 44), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((8, 12, im.width - 8, im.height - 4), 22, fill=(0, 0, 0, 70))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(im).rounded_rectangle((4, 4, im.width - 10, im.height - 14), 22, fill=(255, 255, 255, 245))
    im.alpha_composite(lg, (27, 17)); return im
BADGE = logo_badge()
URL = block_line('nebraskadogwash.com', 40, fg=RED, bg=WHITE, pad=(30, 8), radius=40)

# text items: {"t0":s, "lines":[...], "size":px, "style":"block|plain|white", "y":px, "x":"center|left", "t1":s(optional), "anim":"pop|slide"}
ITEMS = []
for it in SPEC['text']:
    st = it.get('style', 'block')
    spr = []
    for ln in it['lines']:
        if st == 'block': spr.append(block_line(ln, it['size']))
        elif st == 'white': spr.append(block_line(ln, it['size'], fg=RED, bg=WHITE))
        else: spr.append(plain_line(ln, it['size'], stroke=it.get('stroke', 0)))
    ITEMS.append(dict(it, spr=spr))

def paste(base, im, cx, cy, sc=1., alpha=1., rot=0.):
    if sc <= .01 or alpha <= .01: return
    if sc != 1: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def overlay(t):
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # badge drops in
    u = clamp((t - .15) / .45); paste(L, BADGE, W - BADGE.width / 2 - 40, 150 - (1 - eob(u)) * 260, alpha=u)
    for it in ITEMS:
        y = it['y']; gap = it.get('gap', 4)
        for k, s in enumerate(it['spr']):
            t0 = it['t0'] + k * it.get('stagger', .12)
            if 't1' in it and t > it['t1'] + .25: continue
            u = clamp((t - t0) / .42)
            if u <= 0: y += s.height + gap - 30; continue
            out = clamp((t - it['t1']) / .25) if 't1' in it else 0
            xv = it.get('x', 'center')
            x = W / 2 if xv == 'center' else (70 + s.width / 2 if xv == 'left' else float(xv))
            if it.get('anim', 'pop') == 'slide':
                paste(L, s, x + (1 - eoc(u)) * (-W if k % 2 == 0 else W), y + s.height / 2, alpha=1 - out)
            else:
                paste(L, s, x, y + s.height / 2, sc=eob(u) * (1 - .3 * out), alpha=min(1, u * 2) * (1 - out), rot=it.get('rot', 0))
            y += s.height + gap - 30
    u = clamp((t - .9) / .4); paste(L, URL, W / 2, H - 150 + (1 - eoc(u)) * 200, alpha=u)
    return L

def foam(t):
    p = clamp((t - WIPE0) / .6); p = p * p * (3 - 2 * p)
    if p <= 0: return None
    top = H + 150 - (H + 450) * p
    M = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(M)
    if top < H: d.rectangle((0, int(top), W, H), fill=(255, 255, 255, 255))
    r2 = np.random.default_rng(5)
    for k in range(26):
        x = k * 44 + r2.uniform(-10, 10); r = r2.uniform(60, 120); yy = top + 22 * math.sin(k * 1.3 + t * 9)
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=(255, 255, 255, 255))
    for k in range(16):
        x = r2.uniform(0, W); r = r2.uniform(18, 44); yy = top - r2.uniform(100, 240) + 30 * math.sin(t * 6 + k)
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=(255, 255, 255, 230), outline=(215, 225, 235, 255), width=3)
    return M

# ---------------- render main
FR = footage()
tmp = OUT + '.main.mp4'
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', tmp], stdin=subprocess.PIPE)
cuts = []
acc = 0
if SPEC.get('layout', 'seq') == 'seq':
    for c in SPEC['clips'][:-1]: acc += c['dur']; cuts.append(acc)
for i in range(len(FR)):
    t = i / FPS
    fr = Image.fromarray(FR[i]).convert('RGBA')
    for c in cuts:                                     # quick white flash on cuts
        if 0 <= t - c < .1: fr = Image.blend(fr, Image.new('RGBA', (W, H), WHITE + (255,)), .55 * (1 - (t - c) / .1))
    fr.alpha_composite(overlay(t))
    m = foam(t)
    if m: fr.alpha_composite(m)
    enc.stdin.write(fr.convert('RGB').tobytes())
enc.stdin.close(); enc.wait()

# ---------------- join end card + music
mus = SPEC['music']; off = SPEC.get('music_offset', 0)
fc = (f'[0:v][1:v]concat=n=2:v=1:a=0[v];'
      f'[2:a]atrim={off}:{off + 12},asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st=10.6:d=1.4,volume={SPEC.get("music_gain", 0.9)}[m];'
      f'[1:a]adelay={int(MAIN * 1000)}|{int(MAIN * 1000)},volume=1.0[b];'
      f'[m][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', END, '-i', mus, '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                '-t', '12', '-movflags', '+faststart', OUT], check=True)
os.remove(tmp)
print('done', OUT)
