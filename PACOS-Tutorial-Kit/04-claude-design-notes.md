# PACOS — Motion & Design Spec (title cards, lower-thirds, transitions)

So the intro (screen recording) and the outro (AI video) read as **one product**. These
tokens are pulled from the app's own CSS so the video matches the UI exactly.

## Color tokens (from the app)
| Token | Hex | Use in video |
|-------|-----|--------------|
| Accent | `#e84a2f` | The one highlight color: click ripples, key underlines, the "OS" pulse, end-card CTA |
| Ink (dark) | `#0f172a` / near-black | Title-card backgrounds, lower-third bars |
| Off-white bg | `#f7f7f8` (stone-50-ish) | Safe title background; matches app canvas |
| Blue tag | soft indigo | Secondary chips only; use sparingly |
| Confidence green | `#0f6b38` on `#d9f2e4` | If showing the "verified vs predicted" idea |

**Rule:** one accent only. Orange is the star; everything else is slate/ink/off-white.

## Typography
- Headings: a clean geometric/grotesque sans (the app reads as system-sans/Inter-like).
  Bold weight for titles, medium for lower-thirds.
- Code/labels (queries, emails, agent names): a monospace (Consolas / SF Mono) — reuse
  it whenever you show a Boolean query or a predicted email, matching the app's `.mono`.
- Never more than two type sizes on screen at once.

## Motion language (keep it consistent across all 8 intro segments)
| Element | Spec |
|---------|------|
| Title / lower-third in | translateY 12px→0 + opacity 0→1, **300ms ease-out** |
| Title / lower-third out | opacity 1→0, **200ms ease-in** |
| Click ripple | accent-orange circle, scale 0→1.6, opacity 0.5→0, **450ms** |
| Cursor | soft-glow dot, ~1.2× normal size, slight trail |
| Static hold | Ken Burns push-in 3–4% over the clip's length |
| Phase chip cross-fade | DISCOVER→GENERATE→APPROVE→TRACK, **250ms** |
| Screen-to-screen cut | hard cut on action, or 150ms dip-to-white for phase changes |
| Reveal (variant cards, table rows) | stagger children **60ms** apart, each fades+rises 8px |

## The phase chip (top-left throughout)
A small pill that names the current phase, cross-fading as the story moves:
`DISCOVER` (orange) → `GENERATE` (orange) → `APPROVE` (slate) → `TRACK` (slate).
It gives the viewer a map — the Notion-onboarding feel of "you are here."

## Lower-third pattern (for key actions)
When a click has an implication worth naming, drop a one-line lower-third using the
`05-actions-and-implications.md` legend, e.g.:
- On **Generate**: `🔒 drafts only — never auto-sends`
- On **Find People**: `🟡 creates leads · predicted email`
- On **Remove**: `🔴 removes lead + assets`

Keep them ≤5 words, monospace tag + short label, on screen ~2s.

## End card (shared by intro outro)
- Background: ink `#0f172a`, soft orange bokeh drifting.
- PACOS wordmark with the **OS** in accent orange (matches the sidebar brand).
- Tagline: **"Run your job search like a system."**
- One CTA line (your choice): a URL, "Try the tour," or "Start with one lead."
- Hold 3s, gentle music resolve.

## Accessibility / polish
- Captions: burn in the voiceover as subtitles (many watch muted). Style: off-white text,
  subtle dark scrim, bottom-center, same sans.
- Contrast: never put orange text on the off-white bg for anything small — use ink text
  and reserve orange for shapes/underlines.
- Motion restraint: one moving thing at a time. If the UI is animating (agent board),
  hold the camera still.
