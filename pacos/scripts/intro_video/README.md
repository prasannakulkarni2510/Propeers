# Intro video

Rebuilds `frontend/public/pacos-intro.mp4` (and its poster) from the live UI.
Every person and company in the demo data is invented.

1. `python seed_demo.py <demo_dir>`: fictional leads in every stage, drafts, a CV.
2. Run the backend with `LEADS_CSV_PATH`, `TRACKER_CSV_PATH`, `OUTPUT_DIR` and
   `BASE_CV_PATH` pointed into `<demo_dir>` (blank login vars), and `npx vite`.
3. `python capture.py <work>/frames`: 1920x1080 screenshots via Playwright
   (the chat frames use the real model).
4. `python tts.py <work>/voice`: narration from `script.py` (needs `edge-tts`).
5. `python compose.py <work>/frames <work>/scenes`: captioned scene stills.
6. `python build.py <work> pacos-intro.mp4`: zoom, crossfades, loudness-normalised audio.

Poster: `ffmpeg -ss 6 -i pacos-intro.mp4 -frames:v 1 -q:v 3 pacos-intro-poster.jpg`.
