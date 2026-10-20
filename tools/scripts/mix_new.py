# mix_new.py: new Pixabay rotation onto Dogwash v3 Reels that Dan hasn't approved -> repo v/dwm_NNN.mp4
import json,subprocess,os
S='/tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad/'
P='/home/claude/music/pixabay/'; V='/home/claude/nebraska-dogwash-videos/v/'
OFF=json.load(open(P+'offsets.json'))
sets=json.load(open(S+'vid/remix_sets.json'))
m=json.load(open(S+'vid/dw_post_map.json'))
ok=['01','02','04','10','11','12','13','14','18','19','20','22']
files={f[3:5]:f for f in os.listdir(P) if f.endswith('.mp3')}
R=sorted(sets['R'],key=lambda n:m.get(n,{}).get('reel','0000'))
plan={}
for i,n in enumerate(R):
    k='25' if n=='172' else ok[i%len(ok)]
    plan[n]=files[k]
for n,f in plan.items():
    out=V+f'dwm_{n}.mp4'
    if os.path.exists(out): continue
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',f'/home/claude/reels_out/v3/{n}.mp4','-ss',str(OFF[f]),'-t','12.2','-i',P+f,
      '-filter_complex','[1:a]loudnorm=I=-16,afade=t=in:d=0.3,afade=t=out:st=10.8:d=1.2,atrim=0:12[m];[0:a]volume=0.55[s];[m][s]amix=inputs=2:duration=first:normalize=0[a]',
      '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',out],check=True)
json.dump(plan,open('/home/claude/dwsched/new_music_plan.json','w'),indent=0)
print(len(plan),'mixed; uses of 22:',sum(1 for f in plan.values() if f.startswith('px_22')))
