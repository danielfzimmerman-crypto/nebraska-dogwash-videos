# mix_fill.py: for each new Reel, copy dw_NNN.mp4 and make dws2_NNN.mp4 (music baked in) into the repo v/ folder
import json,subprocess,shutil
M='/home/claude/music/'
OFF=json.load(open(M+'offsets.json'))
TR=['00_happybeat.ogg','01_happy-loop.mp3','02_funky-house.mp3','03_sunny-city.ogg','04_joyful-jungle.ogg','06_happy-ukulele.mp3','07_vintage-hawaii.mp3','08_summer-walk.mp3','10_funked-up.mp3','11_funky-disco.ogg','12_raspberry-jam.ogg','14_jam.mp3','15_kalimba.ogg','16_feel-good-summer.ogg','20_summertown.mp3']
AUD=['1388161098514399','423124700418880','1057409882044849','1154971944635968','9759056157508092','2793991050742744','2185456801802676']
NS=['006','028','045','047','048','057','058','063','078','088','099','172','180','181','199','275','283']
V='/home/claude/nebraska-dogwash-videos/v/'
out={}
for i,n in enumerate(NS):
    src=f'/home/claude/reels_out/v2/{n}.mp4'; trk=TR[(i*4+3)%len(TR)]; off=OFF.get('tracks/'+trk,0.0); aud=AUD[i%len(AUD)]
    shutil.copy(src,V+f'dw_{n}.mp4')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',src,'-ss',str(off),'-t','11.7','-i',M+'tracks/'+trk,
      '-filter_complex','[1:a]loudnorm=I=-16,afade=t=in:d=0.3,afade=t=out:st=10.3:d=1.2,atrim=0:11.5[m];[0:a]volume=0.55[s];[m][s]amix=inputs=2:duration=first:normalize=0[a]',
      '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',V+f'dws2_{n}.mp4'],check=True)
    out[n]={'track':trk,'toff':off,'audioId':aud}; print('mixed',n,trk,flush=True)
json.dump(out,open('/home/claude/dwsched/fill_music.json','w'),indent=1)
