# Nebraska Dogwash Reel tools (snapshot Oct 20, 2026)

These are the working files from the Claude session that built the Dogwash Reels. The full handoff is the project doc `claude/nebraska-dogwash-handoff.md`.

## What's in each folder
- `engine/`: the Reel renderer (`engine.py`), the bark sound maker (`make_bark.py`), Poppins fonts and the bark WAVs.
  - End card settings: `LB_SEGS = [(.25, 1.25), (4.27, 7.00)]`, `XF = 0` (hard cut), `DUR = 12.0`.
  - Dan approved this ending. Don't add a crossfade, an extra bark, or a shorter ending.
- `veo_clips/`: the Veo motion clips, one per design (`veo_NNN.mp4`). `veo_logo.mp4` is the end-card dog.
  - `*_veo_rejected` files are the rejected versions. `*_flow` files are alternates.
- `scripts/`: the mixing and render scripts.
  - `mix_v3.py`: writes the `dwe` and `dwes` files.
  - `mix_new.py`: writes the `dwm` files, using the new Pixabay rotation.
  - `run_*.sh`: batch renders.
  - `qc.sh` and `still.sh`: checks and still frames.
- `data/`:
  - `dw_post_map.json`: design number → scheduled Reel and Story times.
  - `remix_sets.json`: A = approved (keeps its old music), D = don't use, R = remixed.
  - `new_music_plan.json`: design number → Pixabay track.
  - `plan4.json` and `fill_music.json`: the old music plans.
  - `plan300.json`, `order.tsv`, `rr_list.txt`, `problems.tsv`.
- `logs/`: Metricool update logs (date, network, uuid, new id), including the covers runs.
- `captions/`: captions per design (`NNN.json`).
- `music/`: `credits.tsv` (title, artist and Pixabay URL for every track), `offsets.json` (the start point used in each track) and `REMOVED_TRACKS.txt`.
  - The MP3s are not stored here, because the Pixabay license doesn't allow standalone redistribution. Re-download them from the URLs in `credits.tsv`.
- `pages/`: source for the review gallery, the music sampler and the fill-in tool.

## Paths
The scripts still point at the old session's paths: `/home/claude/...` and `/tmp/claude-0/.../scratchpad/...`. Update those before you run anything.
