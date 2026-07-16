# PACOS — Screenshot Gallery (captured from the live app)

Real PNGs of every screen **and** the key click-interaction states, saved in
`screenshots/`. Page shots were rendered with headless Chrome; the interaction states
(forms open, chat conversation, import result) were driven with Playwright clicks. All at
1600×1000, from the running app with your real data.

## Page states (reachable by URL)

| File | Screen | Shows |
|------|--------|-------|
| `01-dashboard.png` | Dashboard | Stat row (429 leads), Generate panel, live Agent Status board |
| `02-leads.png` | Leads | Full roster table: Name · Title · Company · LinkedIn · Predicted Email · Domain · Assets · Status · Actions |
| `03-discovery-variants.png` | Discovery | 7 Boolean search variants + the Auto-import "Find People" panel |
| `04-assets.png` | Assets | The four asset tabs; a no-email lead showing the "DM-only" skip |
| `05-approvals.png` | Approvals | Ready-to-send · Awaiting reply · Unmatched replies |
| `06-tracker.png` | Tracker | Whole-pipeline table, per-row status dropdown, Scan inbox |
| `07-chat.png` | Chat | Empty chat with the example prompt hint |

## Interaction states (button clicks — what opens what)

| File | Trigger | Shows / implication |
|------|---------|---------------------|
| `08-add-from-jd-form.png` | Leads → **+ Add lead from JD** | The inline JD paste panel open, text pasted, **Parse JD** ready |
| `09-jd-proposal-review.png` | …→ **Parse JD** | The extracted **proposal** with editable fields — *"nothing is saved until you confirm"* |
| `10-add-manual-form.png` | Leads → **+ Add lead manually** | The manual lead form (all fields + persona) |
| `11-chat-proposal.png` | Chat → describe a person → **Send** | Assistant reply + editable **Proposed lead** card with **Add to leads.csv** & **Find people** |
| `12-find-people-paste.png` | Discovery → **Paste results instead** | The paste box with X-Ray HTML, **Import from pasted results** ready |
| `13-find-people-imported.png` | …→ **Import from pasted results** | Green **"2 lead(s) imported. See the Leads page."** |
| `14-leads-enriched.png` | Leads → search "Acme" | The imported leads with **predicted email + confidence chip** (not `unknown-1`) |
| `15-assets-generated.png` | Assets → generated lead | A populated draft (cold email/DM/cover letter/CV notes) with **Regenerate** / **Copy** |

## How these were produced (to re-capture or refresh)

Page shots (headless Chrome — one command each):
```bash
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size=1600,1000 --virtual-time-budget=6000 --run-all-compositor-stages-before-draw \
  --screenshot="screenshots/02-leads.png" "http://127.0.0.1:8000/leads"
```

Interaction shots need clicks — record them on camera per `06-demo-walkthrough.md`, or
re-drive with a browser-automation tool. Interaction states with no stable URL (open
forms, live chat) cannot be captured by a plain headless URL shot; they must be clicked
into first, which is exactly what these Playwright-driven files did.

> Note: `08`–`15` used a throwaway **Acme Robotics** demo and a **Priya Shah** chat
> example; the demo leads were deleted afterward, so your pipeline is back to 429.
