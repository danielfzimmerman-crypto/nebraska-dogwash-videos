# mix_v3.py: for every finished reels_out/v3/NNN.mp4 make repo v/dwe_NNN.mp4 (copy) and v/dwes_NNN.mp4 (music baked in, 12 s)
import json,subprocess,shutil,os
S='/tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad/'
M='/home/claude/music/'; V='/home/claude/nebraska-dogwash-videos/v/'
OFF=json.load(open(M+'offsets.json'))
T={}
for x in json.load(open(S+'sched/dwv/story_music.json')): T[x['n']]=(x['track'],OFF.get('tracks/'+x['track'],0.0))
for x in json.load(open('/home/claude/dwsched/plan4.json')): T[x['n']]=(os.path.basename(x['track']),x['toff'])
for n,x in json.load(open('/home/claude/dwsched/fill_music.json')).items(): T[n]=(x['track'],x['toff'])
done=0
for f in sorted(os.listdir('/home/claude/reels_out/v3')):
    if not f.endswith('.mp4') or 'tmp' in f: continue
    n=f[:3]; src='/home/claude/reels_out/v3/'+f; out=V+f'dwes_{n}.mp4'
    if os.path.exists(out) and os.path.getmtime(out)>os.path.getmtime(src): continue
    if n not in T: print('NO TRACK',n); continue
    trk,off=T[n]
    if not os.path.exists(M+'tracks/'+trk): print('TRACK REMOVED',n,trk); continue
    shutil.copy(src,V+f'dwe_{n}.mp4')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',src,'-ss',str(off),'-t','12.2','-i',M+'tracks/'+trk,
      '-filter_complex','[1:a]loudnorm=I=-16,afade=t=in:d=0.3,afade=t=out:st=10.8:d=1.2,atrim=0:12[m];[0:a]volume=0.55[s];[m][s]amix=inputs=2:duration=first:normalize=0[a]',
      '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',out],check=True)
    done+=1
print('mixed',done)
