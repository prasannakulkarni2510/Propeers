// All FastAPI calls live here. In dev, BASE is "" and Vite proxies /api.
const BASE = import.meta.env.VITE_API_URL || "";

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(detail);
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

  generate: (body) =>
    req("/api/agents/generate", { method: "POST", body: JSON.stringify(body) }),
  markSent: (body) =>
    req("/api/approvals/sent", { method: "POST", body: JSON.stringify(body) }),
  markReply: (body) =>
    req("/api/approvals/reply", { method: "POST", body: JSON.stringify(body) }),
  markStatus: (body) =>
    req("/api/approvals/status", { method: "POST", body: JSON.stringify(body) }),
};
