# Screen art v2, in the style Dan picked (the "Be a star" screens): blue screen, star dog, touch-to-start menu.
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
FD='/home/claude/nebraska-dogwash-videos/tools/engine/'
F=lambda w,s: ImageFont.truetype(FD+f'Poppins-{w}.ttf',s)
B=(30,91,216); LB=(236,243,252)
def cut(img, key):   # alpha from distance to the flat background colour
    a=np.asarray(img.convert('RGB')).astype(float); d=np.sqrt(((a-np.array(key))**2).sum(-1))
    al=np.clip((d-38)/40,0,1)*255; o=img.convert('RGBA'); o.putalpha(Image.fromarray(al.astype(np.uint8)).filter(ImageFilter.GaussianBlur(.8))); return o
pood=Image.open('poodle.png').convert('RGB'); key=tuple(int(v) for v in np.median(np.asarray(pood)[:40,:40].reshape(-1,3),0))
pc=cut(pood,key)
W,H=1600,900; m=Image.new('RGB',(W,H),B); d=ImageDraw.Draw(m)
d.ellipse((1050,520,2050,1500),fill=LB)                    # light circle bottom-right
d.ellipse((-230,-230,230,230),fill=(255,255,255))          # top-left white corner
logo=Image.open('/tmp/claude-0/-home-claude/f6002c21-a0e6-53cf-a22f-e176f93a0529/scratchpad/flyer/logo_red.png'); logo.thumbnail((170,170)); m.paste(logo,(22,40),logo)
pc=pc.resize((820,820)); m.paste(pc,(640,60),pc)
d.text((120,360),'pamper your pup',font=F(600,40),fill=(200,220,255))
d.text((120,410),'Be a star',font=F(900,96),fill='white')
for x,y,r in ((560,180,26),(1450,140,18),(520,700,34),(1500,420,22)):
    d.ellipse((x-r,y-r,x+r,y+r),outline=(255,255,255),width=4)
m.save('/home/claude/nebraska-dogwash-videos/tools/specs/screen_main.png')
pug=Image.open('pug.png').convert('RGB')
W,H=600,1000; s=Image.new('RGB',(W,H),LB); d=ImageDraw.Draw(s)
d.text((300,60),'Be a star',font=F(800,40),fill=B,anchor='mt'); d.text((300,112),'touch to choose your wash',font=F(600,24),fill=(90,110,150),anchor='mt')
mask=Image.new('L',(W,H),0); ImageDraw.Draw(mask).rounded_rectangle((40,170,560,800),60,fill=255)
p=pug.resize((520,int(pug.height*520/pug.width))); layer=Image.new('RGB',(W,H),LB); layer.paste(p,(40,170-(p.height-630)//2)); s=Image.composite(layer,s,mask); d=ImageDraw.Draw(s)
d.ellipse((215,770,385,940),fill=B); d.text((300,840),'TOUCH',font=F(900,34),fill='white',anchor='mm'); d.text((300,878),'TO START',font=F(800,18),fill=(210,225,255),anchor='mm')
s.save('/home/claude/nebraska-dogwash-videos/tools/specs/screen_side.png')
a=Image.open('/home/claude/nebraska-dogwash-videos/tools/specs/screen_main.png');b=Image.open('/home/claude/nebraska-dogwash-videos/tools/specs/screen_side.png').resize((540,900))
S=Image.new('RGB',(1600+560,900),'gray');S.paste(a,(0,0));S.paste(b,(1610,0));S.resize((1080,450)).save('ui2_prev.jpg')
