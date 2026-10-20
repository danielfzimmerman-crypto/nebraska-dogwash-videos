#!/bin/bash
cd /tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad
mkdir -p vid/logs_fill
run(){ for n in "$@"; do out=/home/claude/reels_out/v2/$n.mp4; [ -f $out ] && [ $out -nt clips/veo_$n.mp4 ] && continue
  nice -n 5 python3 clips/engine.py $n clips/veo_$n.mp4 $out > vid/logs_fill/r$n.log 2>&1 && rm -f $out.v.mp4 $out.sfx.wav && echo "$(date +%I:%M%p) done $n" >> vid/logs_fill/progress.log || echo "$(date +%I:%M%p) FAIL $n" >> vid/logs_fill/progress.log; done; }
run 006 028 045 047 048 057 &
run 058 063 078 088 099 172 &
run 180 181 199 275 283 &
wait; echo finished >> vid/logs_fill/progress.log
