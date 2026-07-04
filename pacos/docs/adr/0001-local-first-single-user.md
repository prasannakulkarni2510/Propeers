# Local-first, single-user — no cloud deployment

PACOS is a personal job-search tool for one operator. We run it locally (uvicorn +
Vite) and keep all state in local files (`tracker.csv`, `output/`) that the user
owns and can open in Excel. We deliberately reject the directory-structure doc's
Netlify + Railway + Supabase deployment: a public cloud deploy would force a real
database (Railway's filesystem is ephemeral, so CSV state would be wiped on every
redeploy), plus authentication, for zero benefit to a single user.

The `netlify.toml`, `railway.toml`, and `Dockerfile` are kept only as an optional
"someday" path and are not part of the supported v1.

_Trade-off:_ if PACOS ever becomes a hosted multi-user product, the storage layer
must move behind an interface and swap CSV for Postgres. We accept that future
rewrite in exchange for near-zero infrastructure today.
