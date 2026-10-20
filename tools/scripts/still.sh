#!/bin/bash
# still.sh NNN -> clips/veo_NNN.mp4 from the template's background image (no Veo motion)
cd /tmp/claude-0/-home-claude/d9cab08f-5d50-5d8b-834e-3f6cee7ec0fd/scratchpad
ffmpeg -v error -y -loop 1 -i pilot/$1_bg.jpg -f lavfi -i anullsrc=r=48000:cl=stereo -t 8 -r 30 -vf "scale=720:900,pad=720:1280:0:190:black,format=yuv420p" -shortest -c:v libx264 -c:a aac clips/veo_$1.mp4
