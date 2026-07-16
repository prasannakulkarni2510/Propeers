# PACOS — Shot List & Capture Recipe

Record each clip at **1920×1080**, browser zoom 100%, hide bookmarks bar. App at
`http://127.0.0.1:8000`. Save files into `screenshots/` with the exact names below so the
intro script (`01-intro-script.md`) references resolve.

For a screen recorder: capture a few seconds of hold before/after each action so the
editor has handles. Move the cursor deliberately — it's on camera.

| File name | Page / URL | State to capture | Action to record |
|-----------|-----------|------------------|------------------|
| `01-dashboard.png` | `/` | 429 leads, agent board idle | Static hold (hook shot) |
| `02-dashboard-generate.png` | `/` | Generate panel + agent board | Click **Dry-run**, board lights up |
| `03-leads-enriched.png` | `/leads` → search `Acme` | 3 Acme rows w/ predicted email + chips | Slow scroll / hold on a Predicted Email cell |
| `04-assets.png` | `/assets/acme-robotics-asha` | Four asset tabs | Click through tabs; hover **Copy** → "Copied ✓" |
| `05-discovery-variants.png` | `/discovery?company=Razorpay&role=Backend%20Engineer&city=Bengaluru` | 7 variant cards + Auto-import panel | Type company, click **Build searches** |
| `06-find-people.png` | `/discovery?...` | Progress pills mid-run | Click **Find People**, capture the pills lighting |
| `07-imported.png` | `/discovery?...` | Paste box + **"3 leads imported."** | Paste demo HTML → **Import from pasted results** |
| `08-approvals.png` | `/approvals` | Ready-to-send + unmatched replies | Click **Mark sent as → DM** |
| `09-tracker.png` | `/tracker` | Pipeline table, status pills | A status pill animating pending→sent |
| `10-chat.png` | `/chat` | Empty chat with prompt hint | (optional) type a describe-a-person line |

## Recommended recording order (single continuous session)
Record the **demo walkthrough** (`06-demo-walkthrough.md`) in one pass — it naturally
produces frames 05 → 06 → 07 → 03 → 02 → 04 → 08 → 09 in the right order, so you get a
coherent screen recording *and* the stills from the same take.

## Capture tips
- Use the demo company **Acme Robotics** so numbers match the script (3 leads imported).
- Run generation in **Dry-run** — visually identical, no key needed, instant.
- For the "Find People" progress pills (frame 06), they animate quickly; record at 60fps
  if possible, then slow to 0.5× in edit for a satisfying reveal.
- After recording, delete the demo leads (clean-up command in `06-demo-walkthrough.md`).

## Crops the editor will want
- Tight crop of one **Predicted Email + MEDIUM chip** (for the S5 zoom-punch).
- Tight crop of the **Agent Status** row (for the S6 sequence light-up).
- Tight crop of the sidebar footer **"never auto-sends"** (for the S8 trust beat).
