# Cloud deployment as one token-gated service on Render

PACOS gains an *online* run mode so the operator can use it from anywhere:
the same single process as the exe (ADR 0004) — FastAPI serving `/api/*` and
the built dashboard — packaged as a Docker image and run as one Render web
service with a persistent disk mounted at `/data` for the workspace. The
blueprint lives in `render.yaml`; the reasoning and platform comparison in
`docs/DEPLOYMENT.md`.

Decisions bundled here:

- **One service, one origin.** The frontend is not hosted separately
  (Vercel/Netlify/Pages were evaluated and rejected — they cannot run the
  stateful backend, and splitting buys a single-operator tool nothing but
  CORS and a second pipeline). FastAPI's existing `frontend/dist` mount is
  the production path in the cloud too.
- **SQLite stays.** The tracker remains `tracker.db` on the disk (ADR 0003).
  Managed Postgres is a *multi-user* trigger, not a scale trigger.
- **Auth is one bearer token.** `PACOS_AUTH_TOKEN`, checked by middleware on
  every `/api/*` call (constant-time; `/api/health` exempt for probes), and
  prompted for once by the dashboard's AuthGate. One operator ⇒ one token;
  accounts/OAuth would be overhead without a second user.
- **Secrets never leave the server.** Model keys are read from the service
  environment; no `VITE_*` secret can exist (Vite inlines those into the
  public bundle). `sync: false` in the blueprint keeps values out of git.
- **CI/CD is git push.** `autoDeploy` + the `/api/health` check gate deploys;
  a failing build never replaces a healthy one.

This *narrows* ADR 0001's "local-first, no cloud" rather than reversing it:
still one operator, still human-in-the-loop, still nothing auto-sent. The
cloud instance is the same workspace-in-a-folder, with the folder now a
mounted disk and the front door now needing a token. Local and exe modes are
unchanged (`PACOS_AUTH_TOKEN` unset ⇒ no gate).

_Trade-off:_ a paid instance (~$7/mo — Render's free tier has no disks and
spins down) and a second copy of the workspace to keep in your head (local
vs. cloud; they do not sync). We accept that for anywhere-access with zero
architectural change. If the two-workspace ambiguity grates, the escape
hatch is making the cloud instance the only workspace and retiring the exe.
