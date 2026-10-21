# build_layers.py SPEC.json ENG_DIR
# Rebuilds the engine inputs for one design from its Canva layout (positions, shapes, text):
#   ENG_DIR/layers/NNN.json   element list the engine animates
#   ENG_DIR/pilot/NNN_overlay.png   all animated graphics (shapes + text + logo) on transparent 1080x1350
#   ENG_DIR/pilot/NNN_preview.png   overlay over the background, for checking
# The spec lists only the overlay elements (background photo / pattern / dog stay in the bg image).
# Text lines are given already wrapped, exactly as Canva wraps them.
import json, sys, io, math, re
from PIL import Image, ImageDraw, ImageFont
import cairosvg

spec = json.load(open(sys.argv[1])); E = sys.argv[2].rstrip('/') + '/'
NUM = spec['num']; W, H = 1080, 1350
FONT = {600: E + 'clips/Poppins-600.ttf', 800: E + 'clips/Poppins-800.ttf', 900: E + 'clips/Poppins-900.ttf'}
SYM = lambda sz: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(sz * .9))
ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
anim = []

def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def place(im, el):
    rot = el.get('rotation', 0) or 0
    if rot:
        cx, cy = el['left'] + el['width'] / 2, el['top'] + el['height'] / 2
        r = im.rotate(-rot, resample=Image.BICUBIC, expand=True)
        ov.alpha_composite(r, (int(round(cx - r.width / 2)), int(round(cy - r.height / 2))))
    else:
        ov.alpha_composite(im, (int(round(el['left'])), int(round(el['top']))))

for el in spec['elements']:
    k = el['kind']
    w, h = int(round(el['width'])), int(round(el['height']))
    if k in ('shape', 'pill', 'card', 'badge'):
        vb = el['viewBox']
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {vb[0]} {vb[1]}" '
               f'preserveAspectRatio="none"><path d="{el["path"]}" fill="{el["color"]}"/></svg>')
        im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert('RGBA')
        if el.get('opacity', 1) < 1: im.putalpha(im.getchannel('A').point(lambda v: int(v * el['opacity'])))
        place(im, el)
    elif k == 'logo':
        lg = Image.open(el['src'] if el['src'] != 'LOGO_CROP' else __import__('os').path.join(__import__('os').path.dirname(sys.argv[1]), 'logo_crop.png')).convert('RGBA')
        bb = lg.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox(); lg = lg.crop(bb)
        sc = min(w / lg.width, h / lg.height); lg = lg.resize((int(lg.width * sc), int(lg.height * sc)), Image.LANCZOS)
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); im.alpha_composite(lg, ((w - lg.width) // 2, (h - lg.height) // 2))
        place(im, el)
    elif k == 'text':
        size = el['fontSize']; f = ImageFont.truetype(FONT[el.get('weight', 900)], size)
        lh = size * el.get('lineHeight', 1.0)
        asc, desc = f.getmetrics()
        im = Image.new('RGBA', (w + 40, int(lh * len(el['lines']) + size)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for i, line in enumerate(el['lines']):
            lw = sum(d.textlength(p_, font=SYM(size) if p_[:1] == '★' else f) for p_ in re.split('(★+)', line) if p_)
            x = {'start': 0, 'center': (w - lw) / 2, 'end': w - lw}[el.get('align', 'start')]
            # Canva centres each line's glyph box in its line slot
            y = i * lh + (lh - (asc + desc)) / 2
            # Poppins has no star glyph: draw stars with a fallback font, like Canva does
            cx = x
            for part in re.split('(★+)', line):
                if not part: continue
                ff = SYM(size) if part[0] == '★' else f
                d.text((cx, y + (size * .08 if ff is not f else 0)), part, font=ff, fill=hexrgb(el['color']) + (255,))
                cx += d.textlength(part, font=ff)
        h = int(round(lh * len(el['lines'])))
        place(im.crop((0, 0, w, max(h, im.getbbox()[3] if im.getbbox() else h))), dict(el, height=h))
        el = dict(el, height=h)
    if el.get('noanim'): continue
    anim.append({key: el[key] for key in ('kind', 'left', 'top', 'width', 'height') } |
                {'rotation': el.get('rotation', 0), 'color': el.get('color'),
                 'text': '\n'.join(el['lines']) if k == 'text' else '', 'fontSize': el.get('fontSize', 0)})

ov.save(E + f'pilot/{NUM}_overlay.png')
json.dump({'num': int(NUM), 'anim': anim}, open(E + f'layers/{NUM}.json', 'w'), indent=1)
bg = Image.open(E + f'pilot/{NUM}_bg.jpg').convert('RGBA'); bg.alpha_composite(ov); bg.convert('RGB').save(E + f'pilot/{NUM}_preview.png')
print('built', NUM, len(anim), 'elements')
