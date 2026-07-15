# Distribute as a frozen single-process exe

The supported way to *run* PACOS day-to-day is a PyInstaller onefile build,
`PACOS.exe`, sitting in the workspace folder. One process does everything:
FastAPI serves the API **and** the built React frontend (`frontend/dist` is
bundled into the exe and mounted with an SPA fallback), so the Vite dev server
is a development tool only. Double-clicking the exe picks the first free port
from 8000, opens the browser, and the console window is the off switch.

Decisions bundled here:

- **Workspace = the exe's folder.** In a frozen build, `config.py` resolves
  the root to the exe's directory instead of the source tree, so `.env`,
  `data/leads.csv`, `tracker.db`, and `output/` live next to `PACOS.exe`.
  The exe is a *launcher pinned to its workspace*, not a portable app; a
  Desktop shortcut is the supported way to launch it from elsewhere.
- **Re-mint, don't auto-update.** A frozen exe goes stale the moment the
  source changes. `build_exe.bat` (committed) rebuilds the frontend and the
  exe in one command; we rebuild after a dev session ends. `dist/`, `build/`,
  and the `.spec` file are gitignored — the 59 MB binary never enters git.
- **The exe is the whole app, including inbox scanning.** Instead of bolting
  a background Gmail poller into the launcher, the inbox monitor is exposed
  as `POST /api/inbox/scan` with a "Scan inbox" button in the UI. `run_monitor`
  is one-shot by design, so a click-triggered scan matches it exactly, works
  identically in dev and exe, and keeps failures visible. Only the one-time
  OAuth bootstrap (`scripts/auth_gmail.py`) remains a dev-mode step.

This supersedes ADR 0001's *run-mode description* (uvicorn + Vite as two
processes) but strengthens its principle: still local-first, still one
operator, still no cloud. The `Dockerfile`/`railway.toml` remain the
unsupported "someday" path noted there.

_Trade-off:_ onefile means a ~59 MB binary, a few seconds of unpack time at
launch, and a mandatory rebuild step to pick up code changes. We accept that
for a genuine double-click experience with zero installed prerequisites. If
startup time ever grates, the escape hatch is PyInstaller onedir (folder +
exe) at the cost of a messier artefact.
