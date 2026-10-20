#!/bin/bash
# usage: qc.sh OUT.jpg NNN... -> raw Veo frames at 0.3s / 4s / 7.7s per clip, one row each
cd /tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad/clips
out=$1; shift; rows=""
for n in "$@"; do for t in 0.3 4 7.7; do ffmpeg -v error -y -ss $t -i veo_$n.mp4 -frames:v 1 -vf "crop=720:900:0:190,scale=200:-1,drawtext=text='$n $t':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black" qc_${n}_$t.jpg; done
ffmpeg -v error -y -i qc_${n}_0.3.jpg -i qc_${n}_4.jpg -i qc_${n}_7.7.jpg -filter_complex hstack=3 qcr_$n.jpg; rows="$rows -i qcr_$n.jpg"; done
ffmpeg -v error -y $rows -filter_complex vstack=$# $out 2>/dev/null || cp qcr_$1.jpg $out
