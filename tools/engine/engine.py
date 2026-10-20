"""Loud motion-graphics engine for Nebraska Dogwash template videos.
usage: python3 engine.py NUM VEO_MP4 OUT_MP4 [preview]
Reads layers/NNN.json + pilot/NNN_{shapes,text}.png, composites animated sprites + suds over the Veo clip,
adds a suds-wave wipe to a white logo end card, synthesizes SFX and mixes with the Veo audio.
"""
import sys, math, json, subprocess, wave, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

S = '/tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad/'
C = S + 'clips/'
NUM = sys.argv[1].zfill(3); VEO = sys.argv[2]; OUT = sys.argv[3]; PREVIEW = len(sys.argv) > 4 and sys.argv[4] != 'x'
W, H, FPS = 1080, 1920, 30
VEO_END = 8.0; WIPE0, WIPE1 = 7.55, 8.15; DUR = 12.0   # 11.5 s: end card settles, then bark + smile ending
TY = 285                                   # template (1080x1350) top inside the 9:16 frame
RED = (192, 34, 53); DARK = (122, 16, 30)
rng = np.random.default_rng(int(NUM))

meta = json.load(open(S + f'layers/{NUM}.json'))
import os, re
if os.path.exists(S + f'pilot/{NUM}_overlay.png'):
    SH = TX = Image.open(S + f'pilot/{NUM}_overlay.png').convert('RGBA')
else:
    SH = Image.open(S + f'pilot/{NUM}_shapes.png').convert('RGBA')
    TX = Image.open(S + f'pilot/{NUM}_text.png').convert('RGBA')
BGIMG = Image.open(S + f'pilot/{NUM}_bg.jpg').convert('RGB') if os.path.exists(S + f'pilot/{NUM}_bg.jpg') else None
# effect rotation: position in the posting order decides the mix so back-to-back posts differ
IDX = 0
try:
    for l in open(S + 'vid/order.tsv'):
        q = l.split('\t')
        if q[1] == str(int(NUM)): IDX = int(q[0])
except Exception: pass
COMBOS = [('paws',), ('marker', 'counter'), ('paws', 'marker'), ('counter',), ('marker',), ('paws', 'counter')]   # shake-off removed per Dan
FX = (set(COMBOS[IDX % 6]) if len(sys.argv) < 6 else set(sys.argv[5].split('+'))) - {'shake'}
WIPE_STYLE = 'squeegee' if IDX % 2 else 'foam'
if len(sys.argv) > 6: WIPE_STYLE = sys.argv[6]
LOGO = Image.open(S + 'pilot/logo_hi.png').convert('RGBA')
F = {w: C + f'Poppins-{w}.ttf' for w in (600, 800, 900)}

# ---------------------------------------------------------------- helpers
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def eoc(t): return 1 - (1 - t) ** 3
def eob(t, s=1.7): t -= 1; return t * t * ((s + 1) * t + s) + 1
def bounce(t):
    n, d = 7.5625, 2.75
    if t < 1 / d: return n * t * t
    if t < 2 / d: t -= 1.5 / d; return n * t * t + .75
    if t < 2.5 / d: t -= 2.25 / d; return n * t * t + .9375
    t -= 2.625 / d; return n * t * t + .984375
def spring(t, k=13, z=5.): return 1 - math.exp(-z * t) * math.cos(k * t)

def paste(base, im, x, y, angle=0, sx=1., sy=1., alpha=1.):
    if alpha <= 0.01 or sx <= .01 or sy <= .01: return
    if sx != 1 or sy != 1:
        im = im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.BILINEAR)
    if angle: im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    base.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2))) if (
        -im.width < x < W + im.width and -im.height < y < H + im.height) else None

def safe_comp(base, im, x, y):
    """alpha_composite that tolerates negative / out-of-frame offsets"""
    x0, y0 = int(x), int(y)
    cx0, cy0 = max(0, -x0), max(0, -y0)
    cx1, cy1 = min(im.width, W - x0), min(im.height, H - y0)
    if cx1 <= cx0 or cy1 <= cy0: return
    base.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x0 + cx0, y0 + cy0))
paste_ = paste
def paste(base, im, x, y, angle=0, sx=1., sy=1., alpha=1.):
    if alpha <= 0.01 or sx <= .01 or sy <= .01: return
    if sx != 1 or sy != 1:
        im = im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.BILINEAR)
    if angle: im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    safe_comp(base, im, x - im.width / 2, y - im.height / 2)

def rot_box(a, pad=14):
    l, t, w, h, r = a['left'], a['top'], a['width'], a['height'], math.radians(a.get('rotation') or 0)
    cx, cy = l + w / 2, t + h / 2
    hw = abs(w / 2 * math.cos(r)) + abs(h / 2 * math.sin(r)); hh = abs(w / 2 * math.sin(r)) + abs(h / 2 * math.cos(r))
    return [cx - hw - pad, cy - hh - pad, cx + hw + pad, cy + hh + pad]

def crop(layer, box):
    b = [int(max(0, box[0])), int(max(0, box[1])), int(min(1080, box[2])), int(min(1350, box[3]))]
    return layer.crop(b), b

def text_sprite(s, size, fill=(255, 255, 255), stroke=DARK, sw=None, weight=900):
    f = ImageFont.truetype(F[weight], size); sw = sw if sw is not None else max(4, size // 11)
    b = f.getbbox(s, stroke_width=sw)
    im = Image.new('RGBA', (b[2] - b[0] + 40, b[3] - b[1] + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((20 - b[0] + 8, 20 - b[1] + 12), s, font=f, fill=(0, 0, 0, 110), stroke_width=sw, stroke_fill=(0, 0, 0, 110))  # drop shadow
    im = im.filter(ImageFilter.GaussianBlur(4))
    d = ImageDraw.Draw(im)
    d.text((20 - b[0], 20 - b[1]), s, font=f, fill=fill + (255,), stroke_width=sw, stroke_fill=stroke + (255,))
    return im

# ---------------------------------------------------------------- build element groups
anim = meta['anim']
texts = [a for a in anim if a['kind'] == 'text']
others = [a for a in anim if a['kind'] != 'text']
def contains(o, a):
    cx, cy = a['left'] + a['width'] / 2, a['top'] + a['height'] / 2
    return o['left'] - 10 <= cx <= o['left'] + o['width'] + 10 and o['top'] - 10 <= cy <= o['top'] + o['height'] + 10 \
        and o['width'] * o['height'] > a['width'] * a['height'] * .6
groups = []        # each: dict(members, kind, box)
used = set()
# logo + card
for o in others:
    if o['kind'] == 'card':
        mem = [o] + [x for x in others if x['kind'] == 'logo' and contains(o, x)]
        groups.append(dict(members=mem, kind='logo')); used.update(id(m) for m in mem)
for o in others:
    if id(o) in used: continue
    inner = [t for t in texts if id(t) not in used and contains(o, t)]
    if inner:
        mem = [o] + inner; used.update(id(m) for m in mem)
        groups.append(dict(members=mem, kind='pill' if o['kind'] in ('pill', 'card') or o['width'] > 1.6 * o['height'] else 'badge'))
for a in anim:
    if id(a) in used: continue
    k = a['kind']
    if k == 'text': k = 'text'
    elif k == 'logo': k = 'logo'
    elif k == 'pill': k = 'pill'
    else: k = 'leaf' if (a.get('color') or '').lower() in ('#e07b39', '#d9a441') or NUM == '183' and k == 'shape' else 'pop'
    groups.append(dict(members=[a], kind=k)); used.add(id(a))

# headline = biggest text with >=4 letters
def letters(a): return sum(ch.isalpha() for ch in a.get('text', ''))
cands = [t for t in texts if letters(t) >= 4]
HEAD = max(cands, key=lambda t: t['fontSize'])
for g in groups:
    boxes = [rot_box(m) for m in g['members']]
    g['box'] = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    shp, b = crop(SH, g['box']); txt, _ = crop(TX, g['box'])
    spr = Image.new('RGBA', shp.size, (0, 0, 0, 0))
    if any(m['kind'] != 'text' for m in g['members']): spr.alpha_composite(shp)
    if any(m['kind'] == 'text' for m in g['members']):
        if all(m['kind'] == 'text' for m in g['members']):   # free-floating copy: soft shadow for readability over video
            pad = 16; big = Image.new('RGBA', (txt.width + 2 * pad, txt.height + 2 * pad), (0, 0, 0, 0))
            sh = Image.new('RGBA', txt.size, (0, 0, 0, 0)); sh.putalpha(txt.getchannel('A').point(lambda v: int(v * .55)))
            big.alpha_composite(sh, (pad + 3, pad + 5)); big = big.filter(ImageFilter.GaussianBlur(6))
            big.alpha_composite(txt, (pad, pad)); spr = big
        else: spr.alpha_composite(txt)
    g['spr'] = spr; g['cx'] = (b[0] + b[2]) / 2; g['cy'] = (b[1] + b[3]) / 2 + TY
    g['head'] = any(m is HEAD for m in g['members'])
    g['mega'] = any(m['kind'] == 'text' and m['fontSize'] >= 120 and m is not HEAD for m in g['members'])
    g['area'] = spr.width * spr.height

# ---------------------------------------------------------------- timeline
EV = []            # (time, sfx kind, x, y)
HOOK_WORDS = HEAD['text'].replace('\n', ' ').split()
if len(HOOK_WORDS) > 4:                       # long headline: slam it as up to 4 short lines, not one word each
    per = math.ceil(len(HOOK_WORDS) / 4)
    HOOK_WORDS = [' '.join(HOOK_WORDS[i:i + per]) for i in range(0, len(HOOK_WORDS), per)]
HOOK_T0, HOOK_DT = .2, .32
hook_end = HOOK_T0 + HOOK_DT * len(HOOK_WORDS) + .25
DOCK0, DOCK1 = hook_end, hook_end + .38
hook_spr = []
for k, w in enumerate(HOOK_WORDS):
    size = 230
    sp = text_sprite(w, size)
    if sp.width > 1000: sp = text_sprite(w, int(size * 1000 / sp.width))
    hook_spr.append(sp)
gap = 6; tot = sum(s.height for s in hook_spr) + gap * (len(hook_spr) - 1)
if tot > 1400:                                # keep the whole stack on screen
    f_ = 1400 / tot; hook_spr = [s.resize((max(1, int(s.width * f_)), max(1, int(s.height * f_))), Image.LANCZOS) for s in hook_spr]
    tot = sum(s.height for s in hook_spr) + gap * (len(hook_spr) - 1)
hook_y = []; yy = 930 - tot / 2
for s in hook_spr: hook_y.append(yy + s.height / 2); yy += s.height + gap
for k in range(len(HOOK_WORDS)): EV.append((HOOK_T0 + k * HOOK_DT + .1, 'slam', W / 2, hook_y[k]))
EV.append((DOCK0 + .02, 'whoosh', W / 2, 930))

# entry schedule for the rest, top-to-bottom, headline group docks
rest = sorted([g for g in groups if not g['head']], key=lambda g: (g['kind'] == 'pop', g['cy']))
t = DOCK1 + .05
for g in rest:
    g['t0'] = t
    t += .2 if g['kind'] != 'pop' else .07
for g in groups:
    if g['head']: g['t0'] = DOCK0 + .8 * (DOCK1 - DOCK0)
# entry styles
for g in rest:
    k = g['kind']
    if k in ('pill', 'badge', 'card'):
        g['side'] = -1 if g['cx'] < W / 2 else 1
        g['dur'] = .32; EV.append((g['t0'], 'whoosh', g['cx'], g['cy'])); EV.append((g['t0'] + g['dur'], 'skid', g['cx'], g['cy']))
    elif k == 'logo':
        g['dur'] = .5; EV.append((g['t0'] + .05, 'pop', g['cx'], g['cy']))
    elif k == 'leaf':
        g['dur'] = 1.1 + rng.uniform(0, .5); g['t0'] -= .2
    elif k == 'pop':
        g['dur'] = .35; EV.append((g['t0'] + .04, 'blip', g['cx'], g['cy']))
    else:  # text
        g['dur'] = .5 if not g['mega'] else .42
        EV.append((g['t0'] + g['dur'] * .45, 'mega' if g['mega'] else 'thump', g['cx'], g['cy']))

# ---------------- extra effects (rotation)
last_entry = max([g['t0'] + g.get('dur', .4) for g in groups] + [DOCK1])
def bg_lum(x, y):
    if BGIMG is None: return 120
    ty = int(y - TY)
    if ty < 0: ty = 2
    if ty >= 1350: ty = 1347
    r_, g_, b_ = BGIMG.getpixel((int(clamp(x, 0, 1079)), ty)); return .3 * r_ + .59 * g_ + .11 * b_
non_head_txt = [g for g in groups if not g['head'] and all(m['kind'] == 'text' for m in g['members'])]
# counter: a single-number text ("15", "ALL FOR $15")
COUNT = None
if 'counter' in FX:
    for g in sorted(groups, key=lambda g: -max(m.get('fontSize') or 0 for m in g['members'])):
        tm = [m for m in g['members'] if m['kind'] == 'text']
        if g['head'] or len(tm) != 1 or '\n' in tm[0]['text']: continue
        if SH is TX and len(g['members']) > 1: continue
        nums = re.findall(r'\d+', tm[0]['text'])
        if len(nums) == 1 and 2 <= int(nums[0]) <= 999 and not re.search(r'\d\s*(AM|PM|am|pm)', tm[0]['text']):
            COUNT = dict(g=g, m=tm[0], val=int(nums[0])); break
    if COUNT is None: FX.discard('counter'); FX.add('marker' if 'marker' not in FX else ('paws' if 'paws' not in FX else 'shake'))
if COUNT:
    COUNT['t0'] = COUNT['g']['t0'] + .05; COUNT['t1'] = COUNT['t0'] + .75
    for k in range(12): EV.append((COUNT['t0'] + k * .062, 'tick', 0, 0))
    EV.append((COUNT['t1'], 'ding', COUNT['g']['cx'], COUNT['g']['cy']))
    EV.append((COUNT['t1'], 'thump', COUNT['g']['cx'], COUNT['g']['cy']))
# marker swipe behind one key line
MARK = None
if 'marker' in FX:
    cands = [g for g in non_head_txt if 28 <= max(m.get('fontSize') or 0 for m in g['members']) <= 120
             and not (COUNT and g is COUNT['g']) and 'nebraskadogwash' not in ''.join(m.get('text', '') for m in g['members']).lower()
             and len(''.join(m.get('text', '') for m in g['members']).replace(' ', '')) >= 4 and g['spr'].width >= 2.2 * g['spr'].height]   # never a lone number badge
    if cands:
        g = max(cands, key=lambda g: max(m.get('fontSize') or 0 for m in g['members']))
        col = (g['members'][0].get('color') or '#ffffff').lower()
        rr, gg, bb = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
        light = .3 * rr + .59 * gg + .11 * bb > 160
        MARK = dict(g=g, t0=max(g['t0'] + .55, last_entry + .15), col=(192, 34, 53, 255) if light else (255, 216, 77, 255))
        EV.append((MARK['t0'], 'marker', g['cx'], g['cy']))
# paw-print stamps walking up to the key element
PAWS = []
if 'paws' in FX:
    # walk across the empty band under the design so prints never cover copy
    by_ = TY + 1350 + (H - TY - 1350) / 2 + 10
    n = 8; pt0 = last_entry + .2; rev = IDX % 2
    for k in range(n):
        x = 110 + k * (W - 220) / (n - 1)
        if rev: x = W - x
        y = by_ + (32 if k % 2 else -32)
        PAWS.append(dict(x=x, y=y, t=pt0 + k * .15, a=(-90 if not rev else 90), col=(192, 34, 53) if bg_lum(x, y) > 150 else (255, 255, 255)))
        EV.append((pt0 + k * .15, 'paw', x, y))
# wet-dog shake-off transition
SHAKEOFF = None
if 'shake' in FX:
    st = max(last_entry + .9, 4.6)
    if st < WIPE0 - 1.0:
        SHAKEOFF = (st, st + .7); EV.append((st, 'shakeoff', W / 2, H / 2))

# camera shake impulses
SHAKES = [(e[0], 26 if e[1] in ('slam', 'mega') else 12 if e[1] in ('thump', 'skid') else 0) for e in EV]
SHAKES = [s for s in SHAKES if s[1]]
def shake(t):
    dx = dy = 0.
    for t0, a in SHAKES:
        u = t - t0
        if 0 <= u < .3:
            e = a * math.exp(-u * 14)
            dx += e * math.sin(u * 95 + t0 * 7); dy += e * math.cos(u * 83 + t0 * 3)
    if SHAKEOFF and SHAKEOFF[0] <= t < SHAKEOFF[1]:
        u = (t - SHAKEOFF[0]) / (SHAKEOFF[1] - SHAKEOFF[0])
        dx += 55 * math.sin(math.pi * u) * math.sin(2 * math.pi * 11 * (t - SHAKEOFF[0]))
        dy += 8 * math.sin(2 * math.pi * 7 * (t - SHAKEOFF[0]))
    return dx, dy
FLASH = [e[0] for e in EV if e[1] in ('slam', 'mega')]

# ---------------------------------------------------------------- particles
SPR_B = None
def make_bubble(r=60):
    s = r * 2 + 8; im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = s / 2
    d.ellipse((c - r, c - r, c + r, c + r), fill=(235, 245, 255, 50), outline=(255, 255, 255, 225), width=max(3, r // 9))
    d.ellipse((c - r * .55, c - r * .65, c - r * .1, c - r * .3), fill=(255, 255, 255, 235))
    d.ellipse((c + r * .25, c + r * .35, c + r * .45, c + r * .5), fill=(255, 255, 255, 150))
    return im
def make_suds(r=60, seed=0):
    g = np.random.default_rng(seed); s = r * 3; im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for _ in range(7):
        rr = r * g.uniform(.35, .6); x = s / 2 + g.uniform(-.55, .55) * r; y = s / 2 + g.uniform(-.4, .4) * r
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(214, 222, 232, 240))
        d.ellipse((x - rr * .92, y - rr * .98, x + rr * .8, y + rr * .7), fill=(255, 255, 255, 250))
    return im.filter(ImageFilter.GaussianBlur(1.2))
SPR_B = make_bubble(); SPR_S = [make_suds(seed=k) for k in range(4)]
# pre-scaled sprite cache (speed)
CACHE = {}
def spr_scaled(kind, idx, sc):
    key = (kind, idx, round(sc * 20))
    if key not in CACHE:
        base = SPR_B if kind == 'b' else SPR_S[idx]
        s = key[2] / 20
        CACHE[key] = base.resize((max(2, int(base.width * s)), max(2, int(base.height * s))), Image.BILINEAR)
    return CACHE[key]
P = []
def emit(t0, x, y, n, vx, vy, g, life, r, kind, spread=(0, 0), dt=0):
    for _ in range(n):
        P.append((t0 + rng.uniform(0, dt), x + rng.uniform(-spread[0], spread[0]), y + rng.uniform(-spread[1], spread[1]),
                  rng.uniform(*vx), rng.uniform(*vy), g, rng.uniform(*life), rng.uniform(*r), kind if kind != 'mix' else rng.choice(['b', 's'])))
def splash(t0, x, y, big=1.):
    n = int(9 * big)
    emit(t0, x - 60, y, n, (-900 * big, -200), (-800, -300), 2300, (.5, .85), (10, 26 * big), 's', (60, 10))
    emit(t0, x + 60, y, n, (200, 900 * big), (-800, -300), 2300, (.5, .85), (10, 26 * big), 's', (60, 10))
    emit(t0, x, y - 20, int(8 * big), (-320, 320), (-420, -140), -60, (.8, 1.4), (10, 26), 'b', (140, 20))
for (t0, kind, x, y) in EV:
    if kind == 'slam': splash(t0, x, y + 60, 1.6)
    elif kind == 'mega': splash(t0, x, y + 40, 1.4)
    elif kind == 'thump':
        if rng.uniform() < .4: splash(t0, x, y + 20, .8)
    elif kind == 'skid' and rng.uniform() < .5:
        emit(t0, x, y, 14, (-650, 650), (-700, -150), 2200, (.6, 1.0), (12, 28), 's', (80, 30))
    elif kind == 'pop':
        for a in np.linspace(0, 2 * np.pi, 16, endpoint=False):
            sp = rng.uniform(300, 600)
            P.append((t0, x, y, math.cos(a) * sp, math.sin(a) * sp - 100, -30, rng.uniform(.6, 1.1), rng.uniform(10, 24), 'b'))
    elif kind == 'blip':
        emit(t0, x, y, 4, (-200, 200), (-260, -60), -40, (.5, .9), (8, 16), 'b', (10, 10))
def make_drop(r=30):
    im = Image.new('RGBA', (r * 2 + 4, r * 3 + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((2, r + 2, 2 + 2 * r, 2 + 3 * r), fill=(200, 230, 255, 200), outline=(255, 255, 255, 240), width=3)
    d.polygon([(r + 2, 2), (4, r * 1.8), (2 * r, r * 1.8)], fill=(200, 230, 255, 200))
    d.ellipse((r * .6, r * 1.6, r * 1.1, r * 2.2), fill=(255, 255, 255, 255))
    return im
SPR_D = make_drop()
if SHAKEOFF:
    for k in range(120):
        a = rng.uniform(0, 2 * math.pi); sp = rng.uniform(700, 1600)
        P.append((SHAKEOFF[0] + rng.uniform(0, .6), W / 2 + rng.uniform(-200, 200), H / 2 + rng.uniform(-300, 300),
                  math.cos(a) * sp, math.sin(a) * sp - 200, 1800, rng.uniform(.5, .9), rng.uniform(14, 30), 'd'))
if COUNT:
    splash(COUNT['t1'], COUNT['g']['cx'], COUNT['g']['cy'] + 30, 1.1)
# fly-in trails
for g in rest:
    if g['kind'] in ('pill', 'badge', 'card'):
        for k in range(8):
            tt = g['t0'] + k * g['dur'] / 8
            p = eoc((tt - g['t0']) / g['dur'])
            x = g['cx'] + g['side'] * (W) * (1 - p)
            emit(tt, x - g['side'] * g['spr'].width / 2, g['cy'] + rng.uniform(-30, 30), 1, (-120, 120), (-160, 20), -60, (.5, .9), (10, 22), 'b')
# ambient rising bubbles throughout
for k in range(0):   # ambient bottom bubbles removed per Dan's feedback (15 Oct)
    P.append((1.0 + k * .22, rng.uniform(40, W - 40), H + 30, rng.uniform(-30, 30), rng.uniform(-260, -130), 0, rng.uniform(3, 6), rng.uniform(12, 36), 'b'))

def draw_particles(L, t):
    for (t0, x0, y0, vx, vy, g, life, r, kind) in P:
        a = t - t0
        if a < 0 or a > life: continue
        x = x0 + vx * a + 6 * math.sin(a * 7 + x0) * (kind == 'b'); y = y0 + vy * a + .5 * g * a * a
        f = a / life
        if kind == 'd':
            sc = r / 30; al = 1 - f ** 3
            key = ('d', 0, round(sc * 20))
            if key not in CACHE: CACHE[key] = SPR_D.resize((max(2, int(SPR_D.width * key[2] / 20)), max(2, int(SPR_D.height * key[2] / 20))))
            spr = CACHE[key].rotate(-math.degrees(math.atan2(vx, -(vy + g * a))), expand=True)
        elif kind == 'b':
            sc = 1.6 * r / 60 * (1 + .9 * max(0, f - .85) / .15); al = 1 if f < .85 else max(0, 1 - (f - .85) / .15)
            spr = spr_scaled('b', 0, sc)
        else:
            sc = 1.6 * r / 60 * (1 - .4 * f); al = 1 - f ** 2; idx = int(x0 + y0) % 4
            spr = spr_scaled('s', idx, sc)
        if al <= 0 or x < -80 or x > W + 80 or y < -80 or y > H + 80: continue
        paste(L, spr, x, y, alpha=al)

# ---------------------------------------------------------------- per-frame overlay
def draw_groups(L, t):
    for g in sorted(groups, key=lambda g: -g['area']):
        t0 = g['t0']; spr = g['spr']; cx, cy = g['cx'], g['cy']
        if t < t0: continue
        u = t - t0; k = g['kind']
        if MARK and g is MARK['g'] and t >= MARK['t0']:
            q = eoc(clamp((t - MARK['t0']) / .35)); mw = (spr.width - 40) * q; mh = spr.height * .62
            if mw > 4:
                hl = Image.new('RGBA', (int(mw) + 2, int(mh)), (0, 0, 0, 0))
                ImageDraw.Draw(hl).rounded_rectangle((0, 0, int(mw), int(mh) - 1), int(mh * .3), fill=MARK['col'])
                paste(L, hl, cx - (spr.width - 40) / 2 + mw / 2, cy + 4, -1.5)
        if COUNT and g is COUNT['g'] and t < COUNT['t1']:
            if t >= COUNT['t0']:
                v = int(round(COUNT['val'] * eoc(clamp((t - COUNT['t0']) / (COUNT['t1'] - COUNT['t0'])))))
                txt = re.sub(r'\d+', str(v), COUNT['m']['text'], count=1)
                key = ('cnt', txt)
                if key not in CACHE:
                    c = COUNT['m'].get('color') or '#ffffff'
                    CACHE[key] = text_sprite(txt, int(COUNT['m']['fontSize'] * 1.02), fill=(int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)), stroke=(0, 0, 0), sw=0, weight=900)
                ss = 1 + .08 * math.sin(t * 60)
                if any(m['kind'] != 'text' for m in g['members']):   # pill behind the number: keep the shape, swap the text
                    shp, _ = crop(SH, g['box']) if SH is not TX else (None, None)
                    if shp is not None: paste(L, shp, cx, cy)
                    else: paste(L, spr, cx, cy, alpha=.0)
                paste(L, CACHE[key], cx, cy + 6, sx=ss, sy=ss)
            continue
        idle = math.sin(2 * math.pi * .6 * (t - t0) + cx * .01) if u > 1 else 0
        if g['head']:
            # docked headline: pop-settle then a gentle breathing pulse
            s = 1 + .25 * math.exp(-7 * u) * math.cos(16 * u) + .02 * idle
            paste(L, spr, cx, cy, sx=s, sy=s, alpha=clamp(u / .08))
        elif k in ('pill', 'badge', 'card'):
            d = g['dur']
            if u < d:
                p = eoc(u / d); x = cx + g['side'] * (W + spr.width / 2) * (1 - p) - g['side'] * 40 * p
                ang = g['side'] * 16 * (1 - p)
                for gh in (3, 2, 1):
                    paste(L, spr, x + g['side'] * gh * 80 * (1 - p), cy, ang, alpha=.13 * gh * (1 - p))
                paste(L, spr, x, cy, ang)
            else:
                s = u - d
                x = cx - g['side'] * 40 * math.exp(-7 * s) * math.cos(15 * s)
                ang = -g['side'] * 10 * math.exp(-5 * s) * math.sin(17 * s) + 1.5 * idle
                paste(L, spr, x, cy + 4 * idle, ang)
        elif k == 'logo':
            s = spring(clamp(u / .9) * 1.6) if u < .9 else 1
            ang = 12 * math.exp(-4 * u) * math.sin(18 * u)
            paste(L, spr, cx, cy, ang, sx=s, sy=s)
        elif k == 'leaf':
            d = g['dur']; p = clamp(u / d)
            x = cx + 70 * math.sin(u * 4 + cx) * (1 - p) ; y = cy - 700 * (1 - eoc(p))
            ang = 50 * math.sin(u * 5 + cy) * (1 - p) + 8 * math.sin(t * 2 + cx)
            paste(L, spr, x, y + 6 * math.sin(t * 2.3 + cx), ang, alpha=clamp(u / .15))
        elif k == 'pop':
            s = spring(clamp(u / .6) * 1.4) if u < .6 else 1
            paste(L, spr, cx, cy + 5 * idle, 30 * (1 - clamp(u / .35)), sx=s, sy=s)
        else:  # text drop with bounce + squash; mega text slams from huge
            d = g['dur']
            if g['mega']:
                if u < d * .45:
                    p = (u / (d * .45)); s = 3.2 - 2.2 * p ** 2
                    paste(L, spr, cx, cy, sx=s, sy=s, alpha=clamp(p * 3))
                else:
                    v = u - d * .45; s = 1 + .14 * math.exp(-9 * v) * math.cos(20 * v) + .03 * idle
                    paste(L, spr, cx, cy, sx=s, sy=s)
            elif max(m.get('fontSize') or 0 for m in g['members']) < 70:
                # small copy: stamp in (scale pop + tilt) so it never crosses other text
                s = spring(clamp(u / .7) * 1.5) if u < .7 else 1
                paste(L, spr, cx, cy + 2 * idle, 14 * (1 - clamp(u / .25)) * (1 if int(cx) % 2 else -1), sx=s, sy=s, alpha=clamp(u / .06))
            else:
                p = clamp(u / d); y = cy - 520 * (1 - bounce(p))
                land = clamp((u - d * .35) / .25); sq = 1 - .2 * math.sin(math.pi * land) if p > .35 else 1
                paste(L, spr, cx, y + 3 * idle, sx=(1 / sq ** .5) if sq < 1 else 1, sy=sq, alpha=clamp(u / .06))

def draw_hook(L, t):
    if t < HOOK_T0 or t > DOCK1: return
    hg = [g for g in groups if g['head']][0]
    if t < DOCK0:
        for k, sp in enumerate(hook_spr):
            ts = HOOK_T0 + k * HOOK_DT
            if t < ts: continue
            u = t - ts
            if u < .12: s = 3.4 - 2.4 * (u / .12) ** 2; al = clamp(u / .05); s = min(s, max(1.08, 1060 / sp.width))   # never wider than the screen
            else: v = u - .12; s = 1 + .12 * math.exp(-10 * v) * math.cos(22 * v); al = 1
            paste(L, sp, W / 2, hook_y[k], -3 if k % 2 else 3, sx=s, sy=s, alpha=al)
    else:
        lin = clamp((t - DOCK0) / (DOCK1 - DOCK0)); p = eob(lin, 1.2)
        # block shrinks/flies to the headline's docked spot
        tw = hg['spr'].width; th = hg['spr'].height
        blk_h = tot; blk_w = max(s.width for s in hook_spr)
        sc = (1 - p) + p * min(tw / blk_w, th / blk_h)
        bx = W / 2 + (hg['cx'] - W / 2) * p; by = 930 + (hg['cy'] - 930) * p
        for k, sp in enumerate(hook_spr):
            oy = (hook_y[k] - 930) * sc
            paste(L, sp, bx, by + oy, 0, sx=sc, sy=sc, alpha=1 - clamp((lin - .8) / .2))

def make_paw(col, s=1.):
    im = Image.new('RGBA', (int(150 * s), int(160 * s)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = col + (235,)
    d.ellipse((35 * s, 70 * s, 115 * s, 145 * s), fill=c)                     # main pad
    for (x, y) in ((22, 48), (55, 18), (95, 18), (128, 48)):
        d.ellipse(((x - 17) * s, (y - 21) * s, (x + 17) * s, (y + 21) * s), fill=c)
    return im
PAW_SPR = {}
def draw_paws(L, t):
    for p_ in PAWS:
        u = t - p_['t']
        if u < 0: continue
        al = 1 - clamp((t - 6.6) / .5)
        if al <= 0: continue
        key = p_['col']
        if key not in PAW_SPR: PAW_SPR[key] = make_paw(key, .75)
        s = 1 + .6 * math.exp(-14 * u) if u < .4 else 1
        paste(L, PAW_SPR[key], p_['x'], p_['y'], p_['a'], sx=s, sy=s, alpha=al * clamp(u / .04))

def overlay(t):
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_paws(L, t); draw_groups(L, t); draw_hook(L, t); draw_particles(L, t)
    return L

# ---------------------------------------------------------------- end card + suds wipe
END = Image.new('RGBA', (W, H), (255, 255, 255, 255))
d = ImageDraw.Draw(END)
for yy in range(-40, H, 120):            # faint bone-pattern dots
    for xx in range((yy // 120 % 2) * 60 - 40, W, 120):
        d.ellipse((xx, yy, xx + 14, yy + 14), fill=(250, 232, 235, 255))
LOGO_BIG = LOGO.resize((760, int(LOGO.height * 760 / LOGO.width)), Image.LANCZOS)
DOG_FRAC = .46       # top part of the logo = the dog drawing
# --- real barking logo: Veo clip (clips/veo_logo.mp4), dog opens mouth + real bark audio
LB_SRC = S + 'clips/veo_logo.mp4'
LB_SEGS = [(.25, 1.25), (4.27, 7.00)]   # two barks (~.35s, ~.90s); splice between two matching howl poses, then the full head turn plays uncut (starts ~4.45s) to the smile
LB_T0, LB_T1 = LB_SEGS[0]
XF = 0                                   # crossfade frames between the segments
LB_LEN = sum(b - a for a, b in LB_SEGS) - XF / FPS
LB_START = DUR - LB_LEN                  # ends exactly at the end of the video
BARKS = (LB_START + .10, LB_START + .65)
def load_logo_bark():
    segs = []
    for a, b in LB_SEGS:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-i', LB_SRC, '-t', str(b - a), '-r', str(FPS),
                              '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        fr = np.frombuffer(raw, np.uint8).reshape(-1, 1280, 720, 3)
        segs.append(np.clip((235 - fr.min(axis=3).astype(float)) / 170, 0, 1))   # ink amount: red lines on white
    al = segs[0]
    for sg in segs[1:]:
        if XF == 0: al = np.concatenate([al, sg]); continue      # hard cut between matching poses: no ghosting blend
        k = np.linspace(0, 1, XF + 2)[1:-1][:, None, None]
        al = np.concatenate([al[:-XF], al[-XF:] * (1 - k) + sg[:XF] * k, sg[XF:]])
    ys, xs = np.where(al.max(axis=0) > .3)
    x0, x1, y0, y1 = xs.min() - 6, xs.max() + 7, ys.min() - 6, ys.max() + 7
    sc = 760 / (x1 - x0); out = []
    for k in range(len(al)):
        a = (al[k, y0:y1, x0:x1] * 255).astype(np.uint8)
        im = np.zeros(a.shape + (4,), np.uint8); im[..., :3] = RED; im[..., 3] = a
        out.append(Image.fromarray(im, 'RGBA').resize((760, int((y1 - y0) * sc)), Image.LANCZOS))
    return out
LOGO_BARK = load_logo_bark() if os.path.exists(LB_SRC) else None
def make_woof():
    t_ = text_sprite('WOOF!', 66, fill=RED, stroke=(255, 255, 255), sw=6, weight=900)
    im = Image.new('RGBA', (t_.width + 120, t_.height + 90), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = im.width / 2, im.height / 2
    for a in range(0, 360, 30):                       # little shout lines
        r1, r2 = t_.width * .52, t_.width * .66
        d.line((cx + r1 * math.cos(math.radians(a)), cy + r1 * .62 * math.sin(math.radians(a)),
                cx + r2 * math.cos(math.radians(a)), cy + r2 * .62 * math.sin(math.radians(a))), fill=RED + (255,), width=6)
    im.alpha_composite(t_, (60, 45)); return im
WOOF = make_woof()
URL = text_sprite('nebraskadogwash.com', 54, fill=RED, stroke=(255, 255, 255), sw=0, weight=800)
ADDR1 = text_sprite('3609 N 90th Street, Omaha NE 68134', 46, fill=(40, 40, 40), stroke=(255, 255, 255), sw=0, weight=800)
ADDR2 = text_sprite('Next door to Nebraska Laundry', 40, fill=RED, stroke=(255, 255, 255), sw=0, weight=600)
TAG = text_sprite('SELF-SERVE DOG WASH', 44, fill=(255, 255, 255), stroke=RED, sw=0, weight=900)
def end_card(t):
    E = END.copy(); u = t - WIPE1
    s = spring(clamp(u / 1.0) * 1.7) if u < 1 else 1 + .015 * math.sin((u - 1) * 5)
    lg = LOGO_BIG; lw, lh = lg.size
    cut = int(lh * DOG_FRAC)
    dog, words = lg.crop((0, 0, lw, cut)), lg.crop((0, cut, lw, lh))
    ang0 = 8 * math.exp(-4 * u) * math.sin(16 * u)
    top = 700 - lh / 2
    # the dog in the logo barks twice near the end: hop + head tilt, then a WOOF burst
    hop = rot = 0
    if LOGO_BARK:
        k = min(len(LOGO_BARK) - 1, max(0, int((t - LB_START) * FPS)))
        fl = LOGO_BARK[k]; top = 700 - fl.height / 2; cut = fl.height * DOG_FRAC
        paste(E, fl, W / 2, 700, ang0, sx=s, sy=s)
    else:
        for bt in BARKS:
            v = t - bt
            if 0 <= v < .22:
                k = math.sin(math.pi * v / .22); hop += 20 * k; rot += 7 * k
        paste(E, words, W / 2, top + cut + (lh - cut) / 2, ang0, sx=s, sy=s)
        paste(E, dog, W / 2, top + cut / 2 - hop, ang0 + rot, sx=s, sy=s)
    for i, bt in enumerate(BARKS):
        v = t - bt
        if 0 <= v < .5:
            q = eob(clamp(v / .12)); al = 1 - clamp((v - .3) / .2)
            bx, by = W / 2 + lw * .42 + i * 70, top + cut * .18 - i * 95
            paste(E, WOOF, bx, by - hop * .5, -12 + 8 * i, sx=q * (1 - .15 * i), sy=q * (1 - .15 * i), alpha=al)
    if u > .45:
        q = eob(clamp((u - .45) / .35))
        pw = TAG.width + 60; pill = Image.new('RGBA', (pw, 96), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle((0, 0, pw - 1, 95), 48, fill=RED + (255,)); pill.alpha_composite(TAG, (30, (96 - TAG.height) // 2 + 4))
        paste(E, pill, W / 2 + (1 - q) * -900, 1030, -2)
    if u > .65:
        q = eoc(clamp((u - .65) / .3))
        paste(E, ADDR1, W / 2, 1160 + 100 * (1 - q), alpha=q)
    if u > .8:
        q = eoc(clamp((u - .8) / .3))
        paste(E, ADDR2, W / 2, 1230 + 100 * (1 - q), alpha=q)
    if u > .95:
        q = eoc(clamp((u - .95) / .3))
        paste(E, URL, W / 2, 1340 + 100 * (1 - q), alpha=q)
    return E

def foam_mask(t):
    """white foam wave rising from the bottom, bubbly crest"""
    p = clamp((t - WIPE0) / (WIPE1 - WIPE0)); p = p * p * (3 - 2 * p)
    top = H + 120 - (H + 360) * p
    M = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(M)
    if top < H - 1:
        d.rectangle((0, int(top), W, H), fill=(255, 255, 255, 255))
        r2 = np.random.default_rng(3)
        for k in range(26):
            x = k * 44 + r2.uniform(-10, 10); r = r2.uniform(50, 110)
            y = top + 20 * math.sin(k * 1.3 + t * 9)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))
        for k in range(14):
            x = r2.uniform(0, W); r = r2.uniform(18, 40); y = top - r2.uniform(90, 200) + 30 * math.sin(t * 6 + k)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 235), outline=(215, 225, 235, 255), width=3)
    return M

# ---------------------------------------------------------------- background video
def probe_box():
    """find the non-black content area of the Veo frame"""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '1', '-i', VEO, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True).stdout
    w, h = 720, len(raw) // 720
    a = np.frombuffer(raw, np.uint8).reshape(h, w)
    rows = np.where(a.mean(1) > 12)[0]; cols = np.where(a.mean(0) > 12)[0]
    return int(cols[0]), int(rows[0]), int(cols[-1] + 1), int(rows[-1] + 1), w, h
x0, y0, x1, y1, vw, vh = probe_box()
cw, ch = x1 - x0, y1 - y0
LETTERBOX = ch < vh - 40
if LETTERBOX:   # content scaled to 1080 wide placed so the 4:5 template area aligns at TY
    sh = int(round(ch * W / cw / 2) * 2)
    VF = f'crop={cw}:{ch}:{x0}:{y0},scale={W}:{sh},fps={FPS}'
    VH = sh
else:
    VF = f'scale={W}:{H},fps={FPS}'; VH = H
BAND = None
# ---- lock the Veo background to its first frame (undo zoom / drift Veo adds), smoothed so it never jitters
import cv2
_STAB = {}
def stab_plan():
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', VEO, '-vf', VF + ',scale=iw/2:ih/2', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
    w2, h2 = W // 2, VH // 2
    orb = cv2.ORB_create(3000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref = None; prm = []
    while True:
        buf = p.stdout.read(w2 * h2)
        if len(buf) < w2 * h2: break
        g = np.frombuffer(buf, np.uint8).reshape(h2, w2)
        kp, de = orb.detectAndCompute(g, None)
        if ref is None: ref = (kp, de); prm.append((1., 0., 0.)); continue
        est = None
        if de is not None and ref[1] is not None:
            m = sorted(bf.match(de, ref[1]), key=lambda x: x.distance)[:600]
            if len(m) >= 12:
                p1 = np.float32([kp[x.queryIdx].pt for x in m]) * 2; p0 = np.float32([ref[0][x.trainIdx].pt for x in m]) * 2
                M, inl = cv2.estimateAffinePartial2D(p1, p0, method=cv2.RANSAC, ransacReprojThreshold=3)
                if M is not None:
                    sc = math.hypot(M[0, 0], M[1, 0]); ni = int(inl.sum())
                    # trust only clear, consistent matches (repeating bone patterns give false ones)
                    if abs(sc - 1) < .35 and ni >= 25 and ni >= .25 * len(m): est = (sc, M[0, 2], M[1, 2])
        prm.append(est if est else prm[-1])
    p.wait()
    a = np.array(prm, float)
    if len(a) > 5:                                   # smooth over time: no frame-to-frame wobble
        k = np.exp(-.5 * (np.arange(-18, 19) / 7.) ** 2); k /= k.sum()
        pad = np.pad(a, ((18, 18), (0, 0)), mode='edge')
        a = np.stack([np.convolve(pad[:, c], k, mode='valid') for c in range(3)], 1)
    # ignore tiny corrections entirely
    if np.abs(a[:, 0] - 1).max() < .006 and np.abs(a[:, 1:]).max() < 2: a[:] = (1, 0, 0)
    return a
def stabilize(im, k):
    if os.environ.get('STAB', '0') != '1': return im          # off: post-stabilizing proved unreliable; Veo prompts hold the layout instead
    if 'plan' not in _STAB: _STAB['plan'] = stab_plan()
    P = _STAB['plan']
    if k == 0: _STAB['ref'] = np.array(im)
    sc, tx, ty = P[min(k, len(P) - 1)]
    if abs(sc - 1) < .001 and abs(tx) < .5 and abs(ty) < .5: return im
    a = np.array(im); h, w = a.shape[:2]
    M = np.float32([[sc, 0, tx], [0, sc, ty]])
    out = cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    valid = cv2.erode(cv2.warpAffine(np.full((h, w), 255, np.uint8), M, (w, h), flags=cv2.INTER_NEAREST), np.ones((5, 5), np.uint8)) > 0
    out[~valid] = _STAB['ref'][~valid]
    return Image.fromarray(out)

def bg_frames():
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', VEO, '-vf', VF, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    last = None; fi = 0
    while True:
        buf = p.stdout.read(W * VH * 3)
        if len(buf) < W * VH * 3:
            while True: yield last
        im = Image.frombytes('RGB', (W, VH), buf)
        im = stabilize(im, fi); fi += 1
        if LETTERBOX:
            fr = Image.new('RGB', (W, H))
            oy = TY - (VH - 1350) // 2
            # extend each column's edge colour into the bands (keeps split layouts split)
            top = im.crop((0, 2, W, 8)).resize((W, 1), Image.BOX).resize((W, max(1, oy)), Image.NEAREST).filter(ImageFilter.BoxBlur(6))
            bot = im.crop((0, VH - 8, W, VH - 2)).resize((W, 1), Image.BOX).resize((W, max(1, H - oy - VH)), Image.NEAREST).filter(ImageFilter.BoxBlur(6))
            fr.paste(top, (0, 0)); fr.paste(bot, (0, oy + VH))
            fr.paste(im, (0, oy)); im = fr
        last = im; yield im

def compose(t, bg):
    # background (Veo clip) stays locked in place; only the overlay graphics move / shake
    fr = bg.convert('RGBA')
    ov = overlay(t)
    dx, dy = shake(t)
    if abs(dx) + abs(dy) > .5:
        ov = ImageChops.offset(ov, int(dx), int(dy))
    fr.alpha_composite(ov)
    # flash on slams
    fl = 0
    for ft in FLASH:
        u = t - ft
        if 0 <= u < .12: fl = max(fl, .35 * (1 - u / .12))
    if t < .12: fl = max(fl, .8 * (1 - t / .12))
    if fl > 0: fr = Image.blend(fr, Image.new('RGBA', (W, H), (255, 255, 255, 255)), fl)
    # suds wipe + end card
    if t >= WIPE0:
        if t >= WIPE1: return end_card(t)
        if WIPE_STYLE == 'squeegee':
            p = clamp((t - WIPE0) / (WIPE1 - WIPE0)); p = p * p * (3 - 2 * p); x = int(-60 + (W + 120) * p)
            E = end_card(WIPE1 - .001)
            if x > 0: fr.paste(E.crop((0, 0, min(W, x), H)), (0, 0))
            draw_squeegee(fr, x, t)
        else:
            fm = foam_mask(t); fr.alpha_composite(fm)
            draw_particles_wipe(fr, t)
    return fr

def draw_squeegee(fr, x, t):
    d = ImageDraw.Draw(fr)
    # water sheet just ahead of the blade
    for k in range(18):
        yy = k * 110 + 40 * math.sin(t * 9 + k); r = 18 + 10 * math.sin(k * 2.1)
        d.ellipse((x + 18, yy - r, x + 18 + 2 * r, yy + r), fill=(225, 240, 255, 210), outline=(255, 255, 255, 255), width=3)
    d.rectangle((x - 22, -10, x + 22, H + 10), fill=(35, 35, 38, 255))           # rubber blade
    d.rectangle((x + 10, -10, x + 22, H + 10), fill=(80, 80, 86, 255))
    d.rounded_rectangle((x - 110, H / 2 - 90, x - 18, H / 2 + 90), 20, fill=(192, 34, 53, 255))  # handle mount
    d.rounded_rectangle((x - 420, H / 2 - 34, x - 100, H / 2 + 34), 34, fill=(192, 34, 53, 255))  # handle
    d.rounded_rectangle((x - 400, H / 2 - 24, x - 260, H / 2 + 24), 24, fill=(140, 20, 36, 255))  # grip

WP = []
for k in range(40):
    WP.append((WIPE0 + rng.uniform(0, .5), rng.uniform(0, W), rng.uniform(-300, 300), rng.uniform(14, 40)))
def draw_particles_wipe(fr, t):
    p = clamp((t - WIPE0) / (WIPE1 - WIPE0)); top = H + 120 - (H + 360) * (p * p * (3 - 2 * p))
    for (t0, x, oy, r) in WP:
        if t < t0: continue
        paste(fr, spr_scaled('b', 0, r / 40), x, top - 60 - oy * .5 - (t - t0) * 300)

# ---------------------------------------------------------------- SFX
SR = 48000
def sfx_track():
    out = np.zeros(int(SR * DUR)); r = np.random.default_rng(5)
    def add(sig, t):
        i = int(t * SR);
        if i < 0 or i >= len(out): return
        out[i:i + len(sig)] += sig[:len(out) - i]
    def env(n, a, d):
        e = np.ones(n); A = max(1, int(a * SR)); e[:A] = np.linspace(0, 1, A); e *= np.exp(-np.linspace(0, d, n)); return e
    def lp(x, k): return np.convolve(x, np.ones(k) / k, mode='same')
    def boom(fr=70, amp=.9, d=.45):
        n = int(d * SR); tt = np.arange(n) / SR
        body = np.sin(2 * np.pi * fr * tt * np.exp(-tt * 4)) * env(n, .002, 7)
        click = r.standard_normal(n) * np.exp(-tt * 80) * .5
        return (body + click) * amp
    def whoosh(d=.35, amp=.5):
        n = int(d * SR); t1 = np.linspace(0, 1, n); return lp(r.standard_normal(n), 14) * np.sin(np.pi * t1) ** 2 * amp
    def skid(d=.45):
        n = int(d * SR); tt = np.arange(n) / SR; f = 2300 + 180 * np.sin(2 * np.pi * 38 * tt) - 600 * tt
        ph = 2 * np.pi * np.cumsum(f) / SR
        return (np.sin(ph) + .35 * np.sin(2 * ph) + .25 * r.standard_normal(n)) * env(n, .01, 5) * .22
    def pop(amp=.4):
        n = int(.05 * SR); tt = np.arange(n) / SR
        return np.sin(2 * np.pi * (2000 + r.uniform(-500, 700)) * tt) * np.exp(-tt * 120) * amp
    def fizz(d=.4, amp=.2):
        n = int(d * SR); x = r.standard_normal(n); x = x - lp(x, 6); return x * env(n, .005, 6) * amp
    def riser(d, amp=.35):
        n = int(d * SR); t1 = np.linspace(0, 1, n); x = lp(r.standard_normal(n), 6) * t1 ** 2 * amp; return x
    add(boom(55, 1.0, .6), 0.0); add(fizz(.5, .3), 0.02)
    for (t0, k, x, y) in EV:
        if k == 'slam': add(boom(62, .95), t0); add(fizz(.35, .22), t0)
        elif k == 'mega': add(boom(50, 1.0, .6), t0); add(fizz(.4, .25), t0)
        elif k == 'thump': add(boom(130, .5, .25), t0); add(fizz(.25, .12), t0)
        elif k == 'whoosh': add(whoosh(), t0 - .05)
        elif k == 'skid': add(skid(), t0); add(fizz(.3, .15), t0)
        elif k == 'pop':
            n = int(.14 * SR); tt = np.arange(n) / SR
            add(np.sin(2 * np.pi * (900 - 2500 * tt) * tt) * env(n, .002, 14) * .6, t0)
        elif k == 'blip': add(pop(.25), t0)
        elif k == 'tick':
            n = int(.03 * SR); tt = np.arange(n) / SR; add(np.sin(2 * np.pi * 3200 * tt) * np.exp(-tt * 200) * .25, t0)
        elif k == 'ding':
            n = int(.9 * SR); tt = np.arange(n) / SR
            add((np.sin(2 * np.pi * 1568 * tt) + .5 * np.sin(2 * np.pi * 3136 * tt)) * np.exp(-tt * 5) * .35, t0)
        elif k == 'marker':
            n = int(.35 * SR); t1 = np.linspace(0, 1, n); x_ = r.standard_normal(n); x_ = x_ - lp(x_, 4)
            add(x_ * (1 + np.sin(2 * np.pi * 30 * t1)) * .5 * np.sin(np.pi * t1) * .18, t0)
        elif k == 'paw': add(boom(170, .35, .18), t0)
        elif k == 'shakeoff':
            n = int(.75 * SR); tt = np.arange(n) / SR
            flap = lp(r.standard_normal(n), 10) * (.5 + .5 * np.sign(np.sin(2 * np.pi * 11 * tt))) * np.sin(np.pi * tt / .75) * .55
            add(flap, t0); add(fizz(.9, .3), t0 + .1)
            for tp in t0 + np.sort(r.uniform(0, .8, 12)): add(pop(.2), tp)
    for tp in np.sort(r.uniform(1.0, 7.4, 22)): add(pop(r.uniform(.1, .25)), tp)
    add(riser(WIPE1 - WIPE0 + .2, .3), WIPE0 - .2); add(whoosh(.6, .6), WIPE0)
    if WIPE_STYLE == 'squeegee':
        n = int((WIPE1 - WIPE0) * SR); tt = np.arange(n) / SR; f = 900 + 700 * tt / (WIPE1 - WIPE0)
        add(np.sin(2 * np.pi * np.cumsum(f) / SR) * (.6 + .4 * np.sin(2 * np.pi * 23 * tt)) * np.sin(np.pi * tt / (WIPE1 - WIPE0)) * .16, WIPE0)
    add(boom(48, 1.0, .7), WIPE1); add(fizz(.8, .3), WIPE1)
    n = int(.14 * SR); tt = np.arange(n) / SR
    add(np.sin(2 * np.pi * (900 - 2500 * tt) * tt) * env(n, .002, 14) * .6, WIPE1 + .05)
    for tp in WIPE1 + np.sort(r.uniform(0, 1.2, 10)): add(pop(.3), tp)
    add(whoosh(.3, .4), WIPE1 + .45); add(boom(140, .45, .25), WIPE1 + .7)
    def bark(f0=560, f1=360, d=.17, amp=.9):
        n = int(d * SR); tt = np.arange(n) / SR
        f = f1 + (f0 - f1) * np.exp(-tt * 18) + 80 * np.exp(-((tt - .02) / .02) ** 2)
        ph = 2 * np.pi * np.cumsum(f) / SR
        src = sum(np.sin(k * ph) / k ** .7 for k in range(1, 14))           # buzzy vocal source
        src += .35 * r.standard_normal(n) * np.exp(-tt * 30)                 # breathy attack
        def bp(x, fc, bw):                                                   # simple 2-pole resonator
            rr = np.exp(-np.pi * bw / SR); th = 2 * np.pi * fc / SR; y = np.zeros_like(x); a1, a2 = 2 * rr * np.cos(th), -rr * rr
            for i in range(2, len(x)): y[i] = x[i] + a1 * y[i - 1] + a2 * y[i - 2]
            return y
        y = bp(src, 900, 350) + .6 * bp(src, 1800, 500) + .25 * bp(src, 3000, 700)
        e = np.minimum(1, tt / .006) * np.exp(-np.maximum(0, tt - .03) * 16)
        y = y * e; return y / (np.abs(y).max() + 1e-9) * amp
    if LOGO_BARK:
        BW = os.environ.get('BARK_WAV', S + 'clips/bark_track.wav')      # pre-timed bark track (barks at +.10s and +.65s)
        if os.path.exists(BW):
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', BW, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout
        else:
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(LB_T0), '-i', LB_SRC, '-t', str(LB_T1 - LB_T0), '-vn', '-ac', '1',
                              '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout
        b = np.frombuffer(raw, np.int16).astype(float) / 32768
        if len(b):
            n = len(b); fade = np.minimum(1, np.arange(n) / (.01 * SR)) * np.minimum(1, (n - np.arange(n)) / (.05 * SR))
            add(np.tanh(b * fade / (np.abs(b).max() + 1e-9) * 1.2) * .45, LB_START)   # bark volume (Dan: was too loud)
    else:
        add(bark(), BARKS[0]); add(bark(600, 400, .15, .8), BARKS[1])
    out = np.clip(out * .9, -1, 1)
    p = OUT + '.sfx.wav'
    with wave.open(p, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((out * 32000).astype(np.int16).tobytes())
    return p

# ---------------------------------------------------------------- render
N = int(DUR * FPS)
if os.environ.get("DBG"): print("FX", FX, WIPE_STYLE, "shake", SHAKEOFF, "last", round(last_entry,2), "drops", sum(1 for q in P if q[8]=="d"))
if PREVIEW:
    want = [float(x) for x in sys.argv[4].split(',')] if sys.argv[4] != 'preview' else [.3, .9, 1.6, 2.3, 3.2, 5, 7.85, 9.5]
    g = bg_frames(); frames = []; i = 0; bg = None
    wi = sorted(int(x * FPS) for x in want)
    for i in range(max(wi) + 1):
        bg = next(g) if i < VEO_END * FPS else bg
        if i in wi: frames.append(compose(i / FPS, bg).convert('RGB').resize((270, 480)))
    sheet = Image.new('RGB', (270 * len(frames), 480))
    for k, f in enumerate(frames): sheet.paste(f, (270 * k, 0))
    sheet.save(OUT); sys.exit()

tmpv = OUT + '.v.mp4'
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-preset', 'veryfast', tmpv], stdin=subprocess.PIPE)
g = bg_frames(); bg = None
for i in range(N):
    if i < VEO_END * FPS: bg = next(g)
    enc.stdin.write(compose(i / FPS, bg).convert('RGB').tobytes())
enc.stdin.close(); enc.wait()
sfx = sfx_track()
has_a = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', VEO],
                       capture_output=True, text=True).stdout.strip()
if os.environ.get('NOVEOAUDIO') or NUM in open(S + 'clips/no_veo_audio.txt').read().split(): has_a = ''
if has_a:
    fc = '[1:a]volume=0.55,aresample=48000,afade=t=out:st=7.4:d=0.6,apad[a1];[2:a]aresample=48000[a2];[a1][a2]amix=inputs=2:duration=longest:normalize=0,atrim=0:10[a]'
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', tmpv, '-i', VEO, '-i', sfx, '-filter_complex', fc, '-map', '0:v', '-map', '[a]']
else:
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', tmpv, '-i', sfx, '-map', '0:v', '-map', '1:a']
subprocess.run(cmd + ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(DUR), '-movflags', '+faststart', OUT], check=True)
print('done', OUT, 'letterbox' if LETTERBOX else 'full', [ (g['kind'], round(g['t0'],2)) for g in groups])
