#!/bin/bash
# re-render Dogwash Reels with the new uncut head-turn ending (12 s) into reels_out/v3
cd /tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad
W=$1; NW=$2; i=0
for n in $(cat vid/rr_list.txt); do i=$((i+1)); [ $((i % NW)) -ne $W ] && continue
  out=/home/claude/reels_out/v3/$n.mp4; [ -f $out ] && continue
  nice -n 3 python3 clips/engine.py $n clips/veo_$n.mp4 $out.tmp.mp4 > vid/logs_fill/rr$n.log 2>&1 && mv $out.tmp.mp4 $out && rm -f $out.tmp.mp4.v.mp4 $out.tmp.mp4.sfx.wav && echo "$(date +%I:%M%p) done $n" >> vid/logs_fill/rr_progress.log || echo "$(date +%I:%M%p) FAIL $n" >> vid/logs_fill/rr_progress.log
done
echo "$(date +%I:%M%p) worker $W finished" >> vid/logs_fill/rr_progress.log
