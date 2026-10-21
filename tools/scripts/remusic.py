# remusic.py OLD_DWM OLD_DWE NEW_RENDER OUT_DWM
# Pixabay is unreachable from the workspace, so the music bed is recovered from the old mix:
# dwm = music + 0.55 * reel audio (mix_new.py), hence music = dwm - 0.55 * dwe (first 10 s, where dwe has audio),
# and for 10-12 s the new render's audio stands in (the end card is identical). Then music + 0.55 * new audio.
import sys, subprocess, numpy as np, wave, tempfile, os
def pcm(f):
    return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',f,'-vn','-ac','2','-ar','48000','-f','f32le','-'],capture_output=True,check=True).stdout,np.float32).reshape(-1,2)
m, e, n = pcm(sys.argv[1]), pcm(sys.argv[2]), pcm(sys.argv[3])
ref = np.zeros_like(m); k = min(len(e), len(m)); ref[:k] = e[:k]; T = 10*48000
j = min(len(n), len(m)); ref[T:j] = n[T:j]
r = np.clip(m - 0.55*ref, -1, 1)
tmp = tempfile.mktemp(suffix='.wav'); w = wave.open(tmp,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000); w.writeframes((r*32767).astype('<i2').tobytes()); w.close()
subprocess.run(['ffmpeg','-v','error','-y','-i',sys.argv[3],'-i',tmp,'-filter_complex','[0:a]volume=0.55[s];[1:a][s]amix=inputs=2:duration=first:normalize=0[a]',
  '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',sys.argv[4]],check=True)
os.remove(tmp); print('mixed', sys.argv[4])
