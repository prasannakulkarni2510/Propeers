// All FastAPI calls live here. In dev, BASE is "" and Vite proxies /api.
const BASE = import.meta.env.VITE_API_URL || "";

// Cloud deployments protect /api/* with PACOS_AUTH_TOKEN; the operator's copy
// lives in localStorage (never in the bundle) and rides along as a Bearer
// header. Empty when auth is off (local / exe usage).
const TOKEN_KEY = "pacos_token";
export const authToken = {
  get: () => localStorage.getItem(TOKEN_KEY) || "",
  set: (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY)),
};

async function req(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = authToken.get();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { headers, ...options });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  health: () => req("/api/health"),
  stats: () => req("/api/stats"),
  leads: () => req("/api/leads"),
  lead: (id) => req(`/api/leads/${id}`),
  assets: (id) => req(`/api/assets/${id}`),
  tracker: () => req("/api/tracker"),
  digest: () => req("/api/tracker/digest"),
  agents: () => req("/api/agents/status"),
  unmatched: () => req("/api/tracker/unmatched"),
  associate: (body) =>
    req("/api/tracker/associate", { method: "POST", body: JSON.stringify(body) }),

  addLead: (body) =>
    req("/api/leads", { method: "POST", body: JSON.stringify(body) }),
  parseJd: (text) =>
    req("/api/leads/parse-jd", { method: "POST", body: JSON.stringify({ text }) }),
  chat: (messages) =>
    req("/api/chat", { method: "POST", body: JSON.stringify({ messages }) }),
  discovery: (body) =>
    req("/api/discovery", { method: "POST", body: JSON.stringify(body) }),
  discoveryForLead: (id) => req(`/api/discovery/${id}`),
  scanInbox: (days = 1) =>
    req(`/api/inbox/scan?days=${days}`, { method: "POST" }),
  jobs: () => req("/api/jobs"),
  generate: (body) =>
    req("/api/agents/generate", { method: "POST", body: JSON.stringify(body) }),
  markSent: (body) =>
    req("/api/approvals/sent", { method: "POST", body: JSON.stringify(body) }),
  markReply: (body) =>
    req("/api/approvals/reply", { method: "POST", body: JSON.stringify(body) }),
  markStatus: (body) =>
    req("/api/approvals/status", { method: "POST", body: JSON.stringify(body) }),
};
