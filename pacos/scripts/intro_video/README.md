# Intro video

Rebuilds `frontend/public/pacos-intro.mp4` as a screen-recording style demo:
a cursor clicks and types through the real app while the camera zooms in on
the action and back out, with narration and captions. Every person and
company in the demo data is invented.

1. `python seed_demo.py <demo_dir>`: fictional leads in every stage, drafts, a CV.
2. Run the backend with `LEADS_CSV_PATH`, `TRACKER_CSV_PATH`, `OUTPUT_DIR` and
   `BASE_CV_PATH` pointed into `<demo_dir>` (blank login vars), and `npx vite`.
3. `python capture_demo.py <work>`: drives the app with Playwright at 2x and
   writes `shots/` plus `storyboard.json` (states, cursor targets, clicks,
   typing frames, camera focus boxes). The chat scenes use the real model.
4. `python tts.py <voice>`: narration for each scene in `script.py` (needs `edge-tts`).
5. `python build_demo.py <work> <voice> pacos-intro.mp4 [--preview 45]`:
   lays out the timeline, then seeks `stage.html` frame by frame and pipes the
   frames to ffmpeg. Needs `playwright` and `imageio-ffmpeg`.

`script.py` and `capture_demo.py` must list the same scenes in the same order.

Motion: one signature easing, cubic-bezier(0.4, 0, 0.2, 1), for the camera and
the cursor; entrances decelerate, exits accelerate; durations 0.15s (click),
0.65s (cursor), 1.0s (camera).

Poster: `ffmpeg -ss 6 -i pacos-intro.mp4 -frames:v 1 -q:v 3 pacos-intro-poster.jpg`.
