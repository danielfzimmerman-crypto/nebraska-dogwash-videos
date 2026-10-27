import json,sys
R='/tmp/claude-0/-home-claude/f6002c21-a0e6-53cf-a22f-e176f93a0529/scratchpad/remake/'
C=lambda n:R+'clips2/'+n+'.mp4'
def B(t0,lines,size,y,**k): return dict(t0=t0,lines=lines,size=size,y=y,style='block',**k)
def Wt(t0,lines,size,y,**k): return dict(t0=t0,lines=lines,size=size,y=y,style='white',**k)
P={
'02':dict(layout='split',clips=[{'file':C('v02a'),'start':0.5},{'file':C('v02b'),'start':1.0}],music='02',
  text=[B(.3,['THIS','OR THAT?'],104,250,stagger=.18),Wt(1.5,['BUBBLES'],52,1560,x=270,rot=-4),Wt(1.75,['TOWEL'],52,1560,x=810,rot=4)]),
'03':dict(clips=[{'file':C('v03'),'start':0.3,'dur':8.15}],music='09',
  text=[B(.3,['STEP 1:'],80,230),B(.55,['CHOOSE','A STATION'],104,350,stagger=.14),Wt(2.2,['THE CUBE OR CYBERWASH'],46,1480,rot=-2)]),
'04':dict(clips=[{'file':C('v04'),'dur':8.15}],music='11',
  text=[B(.3,['TRICK','OR BATH?'],112,270,stagger=.18),Wt(2.0,['HAPPY HOWL-OWEEN, PUPSTOMERS!'],44,1560,rot=-2)]),
'05':dict(clips=[{'file':C('v05'),'dur':8.15}],music='11',
  text=[B(.3,['HAPPY'],96,250),B(.5,['HOWL-OWEEN!'],104,370),Wt(2.3,['SPOOKY CLEAN IN 15 MINUTES'],46,1560,rot=2)]),
'07':dict(clips=[{'file':C('v07'),'dur':8.15}],music='03',
  text=[B(.3,["THAT'S","THE SPOT!"],108,250,stagger=.16),Wt(2.2,['15 MINUTES = $15'],56,1520,rot=-3)]),
'08':dict(clips=[{'file':C('v08'),'dur':8.15}],music='07',
  text=[B(.3,["THAT'S","THE SPOT!"],108,250,stagger=.16),Wt(2.4,['WARM WATER. NO MESS AT HOME.'],44,1560,rot=2)]),
'09':dict(clips=[{'file':C('v09'),'dur':8.15}],music='10',
  text=[B(.3,["WHAT'S YOUR","PUP'S BATH STYLE?"],80,250,stagger=.16),
        Wt(2.0,['A) SPA DAY'],50,1330,x='left'),Wt(2.3,['B) QUICK RINSE'],50,1430,x='left'),Wt(2.6,['C) ZOOMIES AFTER'],50,1530,x='left')]),
'10':dict(clips=[{'file':C('v10'),'dur':8.15}],music='12',
  text=[B(.3,['TEAM BUBBLES','OR TEAM TOWEL?'],86,250,stagger=.16),Wt(2.3,['TELL US BELOW!'],52,1420,rot=-3)]),
'11':dict(clips=[{'file':C('v11a'),'dur':2.7},{'file':C('v11b'),'start':.5,'dur':2.7},{'file':C('v11c'),'dur':2.75}],music='07',
  text=[B(.25,['SPA DAY?'],104,300,t1=2.45),B(2.95,['QUICK RINSE?'],104,300,t1=5.15),B(5.65,['ZOOMIES AFTER?'],96,300),Wt(.9,["WHAT'S YOUR PUP'S STYLE?"],46,1560)]),
'12':dict(clips=[{'file':C('v12'),'dur':8.15}],music='05',
  text=[B(.3,['CAPTION','THIS!'],120,250,stagger=.18),Wt(2.2,['BEST CAPTION WINS BRAGGING RIGHTS'],40,1560,rot=-2)]),
}

P['01']=dict(clips=[{'file':C('p01a'),'dur':1.6},{'file':C('v01'),'start':6.0,'dur':1.6},{'file':C('aBern'),'dur':.75},{'file':C('aBern'),'start':3.3,'dur':1.5},
  {'file':C('aNewf'),'dur':.75},{'file':C('aNewf'),'start':2.9,'dur':1.95}],music='04',
  text=[B(.2,['BEFORE'],110,260,t1=1.45),B(1.65,['AFTER'],110,260,t1=3.05),B(3.25,['BEFORE'],110,260,t1=3.8),B(4.0,['AFTER'],110,260,t1=5.3),
        B(5.5,['BEFORE'],110,260,t1=6.0),B(6.25,['AFTER'],110,260),Wt(6.4,['FRESH, CLEAN & FABULOUS'],50,1500,rot=-2)])
P['06']=dict(clips=[{'file':C('v06'),'dur':3.2},{'file':C('aBrush'),'start':.5,'dur':2.5},{'file':C('aDry'),'start':.5,'dur':2.45}],music='06',
  text=[B(.3,["YOUR DOG'S",'NEW FAVORITE SPA'],88,240,stagger=.16),Wt(3.4,['BRUSH'],56,1400,rot=-3,t1=5.5),Wt(5.85,['BLOW DRY'],56,1400,rot=3)])
P['13']=dict(clips=[{'file':C('v13a'),'dur':2.6},{'file':C('aSpray'),'dur':2.8},{'file':C('v13b'),'dur':2.75}],music='08',
  text=[B(.3,['BATH TIME','AT HOME?'],100,250,stagger=.16,t1=2.35),B(2.85,['NO MESS','AT HOME'],100,250,stagger=.16),Wt(5.7,['15 MINUTES = $15'],56,1500,rot=-3)])
P['14']=dict(clips=[{'file':C('v14'),'dur':2.8},{'file':C('aScrub'),'dur':2.7},{'file':C('aNewf'),'start':2.9,'dur':2.65}],music='01',
  text=[B(.3,['$15 FOR','15 MINUTES'],108,250,stagger=.16),Wt(2.9,['EVERYTHING INCLUDED'],52,1380,rot=-2),Wt(5.6,['+$1 EACH EXTRA MINUTE'],46,1480,rot=2)])
for k,v in P.items():
  v['music']=R+'music/norm/'+v['music']+'.mp3'; v['logo']='/home/claude/nebraska-dogwash-videos/tools/specs/logo_crop.png'; v['endcard']=R+'endcard/endcard.mp4'
  json.dump(v,open(R+f'specs/p{k}.json','w'),indent=1)
print(list(P))
