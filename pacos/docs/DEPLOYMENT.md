# Deploying PACOS online

How to run PACOS as a private web app you can reach from anywhere, and why the
architecture is what it is. The committed artifacts:

| File | Purpose |
| --- | --- |
| `pacos/Dockerfile` | Multi-stage image: builds the React dashboard, then a Python runtime serving API + dashboard from one process |
| `render.yaml` (repo root) | Render blueprint: web service + persistent disk + env var wiring |
| `PACOS_AUTH_TOKEN` (backend/main.py) | Bearer-token gate on `/api/*` so the deployment is private |

## Architecture in one paragraph

PACOS stays a **single process**: FastAPI serves `/api/*` *and* the built
`frontend/dist` with an SPA fallback — exactly the shape the frozen exe
already uses (ADR 0004). Deploying is therefore "run that one container in
the cloud, give it a small persistent disk for the workspace
(`leads.csv`, `tracker.db`, `output/`), protect it with a token". No separate
frontend host, no CORS, no second deploy pipeline, one URL.

```
Browser ──HTTPS──▶ Render web service (Docker)
                    ├── FastAPI  /api/*   (Bearer PACOS_AUTH_TOKEN)
                    ├── static   /        (frontend/dist, SPA fallback)
                    └── /data (persistent disk): leads.csv · tracker.db · output/
                          └──▶ NVIDIA NIM API (Nemotron) — key stays server-side
```

## Platform comparison

The decisive constraint: PACOS's backend is **stateful Python** (SQLite +
files on disk) that calls an **AI API with a secret key**. That immediately
splits the field:

| Platform | Runs the FastAPI backend? | Persistent disk | Secrets | Cost for PACOS | Verdict |
| --- | --- | --- | --- | --- | --- |
| **GitHub Pages** | No — static files only | No | None (anything shipped is public) | Free | Ruled out: no backend, and the NVIDIA key would have to live in the browser |
| **Netlify** | Serverless functions only (stateless, short-lived) | No | Env vars for functions | Free tier | Fine for the *frontend alone*; can't run uvicorn or keep SQLite. Would force a split deployment |
| **Vercel** | Python serverless functions (stateless) | No | Good env var UI | Free tier | Same story as Netlify: great DX for Next.js, wrong shape for a stateful FastAPI + SQLite app |
| **Cloudflare Pages** | Workers (JS/WASM runtime) | No (KV/D1/R2 instead) | Good | Generous free | Would mean rewriting the backend around Workers + D1 — a migration, not a deployment |
| **Railway** | Yes — containers | Volumes | Good | Usage-based, ~$5/mo minimum after trial | Solid choice; slightly less predictable billing |
| **Fly.io** | Yes — containers (Machines) | Volumes | Good (`fly secrets`) | ~$2–5/mo | Solid choice; most control, most ops burden (CLI-driven, no git-push deploys out of the box) |
| **Render** | Yes — containers or native Python | Persistent disks | Good (dashboard + `sync: false` in blueprint, secrets never in git) | **$7/mo Starter** (disk requires a paid instance) | **Recommended** |

**Recommendation: Render.** Reasons, in order:

1. **Fits the app's shape** — a long-running process with a disk. No rewrite,
   no split hosting, the Dockerfile is the whole story.
2. **CI/CD for free** — `autoDeploy: true` redeploys on every push to the
   tracked branch; `render.yaml` keeps the infrastructure in git (reviewable,
   reproducible) while secrets stay out (`sync: false`).
3. **Secret management** — keys live in the dashboard/environment, reachable
   only by the server process. Nothing AI-related ever reaches the client.
4. **HTTPS + domain** — `pacos.onrender.com` with TLS out of the box; custom
   domains are a CNAME + one click, certificates auto-renew.
5. **Predictable cost** — flat $7/mo Starter + $0.25/GB disk. Railway and
   Fly are close seconds; pick Railway if you prefer usage-based billing,
   Fly if you want regions/CLI control.

The free-tier caveat: Render's free web services **spin down** after 15 idle
minutes and **don't support disks**. For a tool whose tracker must never lose
state, the $7 Starter instance is the honest MVP floor. (Fly.io can squeeze
under that, at the cost of managing machines yourself.)

### Why not split frontend/backend across two platforms?

`frontend/netlify.toml` exists from an earlier experiment, and the code still
supports a split (`VITE_API_URL`, `CORS_ORIGINS`). It works, but for a
single-operator tool it buys nothing and costs: two deploys to keep in sync,
CORS + preflight complexity, and the API URL baked into the client bundle at
build time. The single-service deployment has one origin and zero of those
problems. Keep the split option in the back pocket for a future multi-user
PACOS where the frontend needs a CDN.

## Each concern, answered

- **Frontend hosting** — served by FastAPI from the same container (built in
  the Docker stage 1). No separate host.
- **Backend hosting** — Render web service (Docker runtime), Starter plan.
- **Database** — SQLite on the persistent disk (`/data/tracker.db`). Right
  answer while PACOS is single-user by design (ADR 0001/0003): zero ops, easy
  backups (download the file), transactional. The migration trigger to
  managed Postgres (Neon/Supabase) is *multi-user*, not scale — one operator
  will never stress SQLite.
- **Authentication** — single-operator bearer token (`PACOS_AUTH_TOKEN`).
  The backend middleware 401s any `/api/*` call without
  `Authorization: Bearer <token>`; the dashboard prompts once and stores it
  in `localStorage`. Constant-time comparison, `/api/health` stays open for
  uptime probes. A full OAuth/user-account system would be pure overhead for
  one user — add it only if PACOS ever becomes multi-tenant (then: Clerk or
  Auth0 free tier, or FastAPI + `authlib`).
- **File storage** — generated assets live in `/data/output` on the disk.
  Object storage (R2/S3) becomes worth it only when assets must survive the
  service or be served publicly.
- **Environment variables & secrets** — see the next section.
- **Domain & HTTPS** — automatic `*.onrender.com` TLS; custom domain = add a
  CNAME, Render provisions the cert. HTTP redirects to HTTPS by default.
- **CI/CD** — git push → Render builds the Dockerfile → health check
  (`/api/health`) must pass → traffic switches. Failed builds never replace a
  healthy deploy. Run `pytest` in GitHub Actions before merge if you want a
  test gate in front of that.
- **Monitoring & logging** — uvicorn access/error logs stream in the Render
  dashboard (exportable via log streams later). Point a free UptimeRobot
  monitor at `https://<app>/api/health` for downtime alerts. That is the
  right amount of observability for an MVP; Sentry's free tier is the first
  upgrade when you want tracebacks aggregated.

## Secrets: how keys stay off the client

The rule the deployment enforces: **a secret may live in the server's
environment or in the operator's head — never in git, never in the bundle.**

1. **Server-side only.** `NVIDIA_API_KEY`, `HF_TOKEN`, and Gmail credentials
   are read by `config.py` from the *server* process environment. Every
   Nemotron call happens in the backend; the browser only ever talks to
   `/api/*`. The key cannot appear in the client because no client code path
   ever sees it.
2. **Nothing secret at build time.** Vite inlines any `VITE_*` variable into
   the public JS bundle — that is why *no* secret is ever named `VITE_*`.
   PACOS's frontend build takes no env vars at all in the single-service
   deployment (`VITE_API_URL` stays empty → relative `/api` calls).
3. **Git hygiene.** `.env` is gitignored; `.env.example` documents shape, not
   values. In `render.yaml`, secrets are declared `sync: false` — the
   blueprint says *that they exist*, their values are typed once into the
   dashboard (encrypted at rest, masked in the UI).
4. **The client holds exactly one credential** — the operator's own
   `PACOS_AUTH_TOKEN`, entered by the operator, kept in `localStorage`. It
   grants access to *their own* deployment and nothing else; rotating it is
   editing one env var and refreshing the page.
5. **Rotation drill** (if a key ever leaks): revoke at the provider
   (build.nvidia.com), set the new value in Render → environment, redeploy.
   No code change, no commit.

## Deploy steps

1. Push the repo to GitHub (with `render.yaml` at the root).
2. [dashboard.render.com](https://dashboard.render.com) → New → Blueprint →
   pick the repo. Render reads `render.yaml` and creates the service + disk.
3. Fill the `sync: false` env vars (NVIDIA key, candidate identity); note the
   generated `PACOS_AUTH_TOKEN` value.
4. Open `https://pacos-<hash>.onrender.com`, paste the token at the gate.
5. Seed the workspace: add leads through the UI (Add-lead form / JD parser /
   Chat) — `leads.csv` and `tracker.db` are created on the disk on first use.

Gmail inbox scanning needs `credentials.json`/`token.json` on the disk; mint
`token.json` locally (`scripts/auth_gmail.py`) and copy both via the service
Shell tab, or skip inbox scanning in the cloud — everything else degrades
gracefully (the scan button reports 503 with instructions).

## Local parity check

```bash
docker build -t pacos ./pacos
docker run --rm -p 8000:8000 -v pacos-data:/data \
  -e LEADS_CSV_PATH=/data/leads.csv -e TRACKER_CSV_PATH=/data/tracker.csv \
  -e NEW_JOBS_CSV_PATH=/data/new_jobs.csv -e OUTPUT_DIR=/data/output \
  -e PACOS_AUTH_TOKEN=dev-token -e NVIDIA_API_KEY=$NVIDIA_API_KEY pacos
# → http://localhost:8000 (token: dev-token)
```
