// All FastAPI calls live here. In dev, BASE is "" and Vite proxies /api.
const BASE = import.meta.env.VITE_API_URL || "";

// Cloud deployments protect /api/* behind a login; the session token returned
// by /api/login lives in localStorage (never in the bundle) and rides along as
// a Bearer header. Empty when auth is off (local / exe usage).
const TOKEN_KEY = "pacos_token";
export const authToken = {
  get: () => localStorage.getItem(TOKEN_KEY) || "",
  set: (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY)),
};

// Header values must be ISO-8859-1. A pasted masked value ("••••") would make
// fetch itself throw before any request — treat such a token as absent so the
// 401 flow (and the AuthGate) can recover instead of bricking every call.
const headerSafe = (t) => /^[\x21-\x7E]+$/.test(t);

// A visitor's temporary CV. sessionStorage belongs to this one tab and the
// browser deletes it when the tab closes; the server only ever receives it
// inside a generate request and never stores it.
const SESSION_CV_KEY = "pacos_session_cv";
export const sessionCv = {
  get: () => {
    try { return sessionStorage.getItem(SESSION_CV_KEY) || ""; } catch { return ""; }
  },
  set: (text) => {
    try {
      if (text && text.trim()) sessionStorage.setItem(SESSION_CV_KEY, text);
      else sessionStorage.removeItem(SESSION_CV_KEY);
    } catch { /* storage blocked: the temporary CV just isn't kept */ }
  },
};
const withSessionCv = (body) => {
  const cv = sessionCv.get();
  return cv ? { ...body, cv_text: cv } : body;
};

async function req(path, options = {}, contentType = "application/json") {
  const headers = { "Content-Type": contentType };
  const token = authToken.get();
  if (token && headerSafe(token)) headers["Authorization"] = `Bearer ${token}`;
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
  login: (email, password) =>
    req("/api/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  loginTrial: () => req("/api/login/trial"),
  stats: () => req("/api/stats"),
  leads: () => req("/api/leads"),
  lead: (id) => req(`/api/leads/${id}`),
  assets: (id) => req(`/api/assets/${id}`),
  regenerateAsset: (id, asset) =>
    req(`/api/assets/${id}/regenerate`, {
      method: "POST",
      body: JSON.stringify(withSessionCv({ asset })),
    }),
  tracker: () => req("/api/tracker"),
  digest: () => req("/api/tracker/digest"),
  agents: () => req("/api/agents/status"),
  unmatched: () => req("/api/tracker/unmatched"),
  associate: (body) =>
    req("/api/tracker/associate", { method: "POST", body: JSON.stringify(body) }),

  addLead: (body) =>
    req("/api/leads", { method: "POST", body: JSON.stringify(body) }),
  deleteLead: (id) => req(`/api/leads/${id}`, { method: "DELETE" }),
  parseJd: (text) =>
    req("/api/leads/parse-jd", { method: "POST", body: JSON.stringify({ text }) }),
  chat: (messages) =>
    req("/api/chat", { method: "POST", body: JSON.stringify({ messages }) }),
  discovery: (body) =>
    req("/api/discovery", { method: "POST", body: JSON.stringify(body) }),
  enrich: (body) =>
    req("/api/discovery/enrich", { method: "POST", body: JSON.stringify(body) }),
  discoveryForLead: (id) => req(`/api/discovery/${id}`),
  scanInbox: (days = 1) =>
    req(`/api/inbox/scan?days=${days}`, { method: "POST" }),
  jobs: () => req("/api/jobs"),
  generate: (body) =>
    req("/api/agents/generate", { method: "POST", body: JSON.stringify(withSessionCv(body)) }),
  markSent: (body) =>
    req("/api/approvals/sent", { method: "POST", body: JSON.stringify(body) }),
  markReply: (body) =>
    req("/api/approvals/reply", { method: "POST", body: JSON.stringify(body) }),
  markStatus: (body) =>
    req("/api/approvals/status", { method: "POST", body: JSON.stringify(body) }),

  getCv: () => req("/api/settings/cv"),
  saveCv: (content) =>
    req("/api/settings/cv", { method: "PUT", body: JSON.stringify({ content }) }),
  // Raw file bytes in the body (no multipart dependency on the backend).
  // Returns extracted text only; saving is a separate saveCv call.
  extractCv: (file) =>
    req(
      `/api/settings/cv/extract?filename=${encodeURIComponent(file.name)}`,
      { method: "POST", body: file },
      "application/octet-stream",
    ),
};
