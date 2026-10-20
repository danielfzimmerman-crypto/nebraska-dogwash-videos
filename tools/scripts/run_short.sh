#!/bin/bash
# render 11.5 s Dogwash videos for every template that has layers but no finished video
cd /tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad
for n in $(python3 -c "import json;print(' '.join(json.load(open('vid/plan300.json'))['ready']))"); do
  out=/home/claude/reels_out/v2/$n.mp4; [ -f $out ] && continue
  [ -f clips/veo_$n.mp4 ] || bash vid/still.sh $n
  nice -n 5 python3 clips/engine.py $n clips/veo_$n.mp4 $out > vid/logs2/r$n.log 2>&1 && rm -f $out.v.mp4 $out.sfx.wav && echo "$(date +%I:%M%p) done $n" >> vid/logs2/progress.log || echo "$(date +%I:%M%p) FAIL $n" >> vid/logs2/progress.log
done
echo "$(date +%I:%M%p) finished" >> vid/logs2/progress.log
