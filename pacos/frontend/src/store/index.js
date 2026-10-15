// Global app state (Zustand). Holds leads, stats, agents, and the async actions
// that talk to the backend and keep everything in sync.
import { create } from "zustand";
import { api } from "../services/api";

export const useStore = create((set, get) => ({
  leads: [],
  stats: null,
  agents: [],
  unmatched: [],
  loading: false,
  generating: false, // global so the "Generating…" state survives tab switches
  error: "",
  toast: "",
  cvIsSample: null, // null until CvEditor has loaded it; drives the setup checklist

  setToast: (toast) => set({ toast }),
  clearToast: () => set({ toast: "" }),
  clearError: () => set({ error: "" }),
  setCvIsSample: (cvIsSample) => set({ cvIsSample }),

  refresh: async () => {
    set({ loading: true, error: "" });
    try {
      const [leads, stats, agents, unmatched] = await Promise.all([
        api.leads(),
        api.stats(),
        api.agents(),
        api.unmatched(),
      ]);
      set({ leads, stats, agents, unmatched, loading: false });
    } catch (e) {
      set({ error: e.message, loading: false });
    }
  },

  generate: async ({
    dry_run = false,
    limit = 0,
    lead_id = null,
    review_hooks = false,
    only_missing = true,
  } = {}) => {
    if (get().generating) return; // guard against double-clicks / re-entry
    set({ error: "", generating: true });
    try {
      const res = await api.generate({ dry_run, limit, lead_id, review_hooks, only_missing });
      if (res.requested === 0) {
        set({ toast: "All leads already have assets, nothing new to build. Use Regenerate on a lead to rebuild." });
      } else {
        const mode = res.dry_run ? "dry-run" : res.model;
        set({ toast: `Generated ${res.generated}/${res.requested} via ${mode}` });
      }
      await get().refresh();
      return res;
    } catch (e) {
      set({ error: e.message });
      throw e;
    } finally {
      set({ generating: false });
    }
  },

  addLead: async (fields) => {
    set({ error: "" });
    try {
      const res = await api.addLead(fields);
      set({ toast: res.message });
      await get().refresh();
      return res;
    } catch (e) {
      set({ error: e.message });
      throw e;
    }
  },

  deleteLead: async (lead_id) => {
    set({ error: "" });
    try {
      const res = await api.deleteLead(lead_id);
      set({ toast: res.message });
      await get().refresh();
    } catch (e) {
      set({ error: e.message });
      throw e;
    }
  },

  associate: async (reply_id, lead_id) =>
    get()._act(() => api.associate({ reply_id, lead_id }), (res) => res.message),

  markSent: async (lead_id, channel) =>
    get()._act(() => api.markSent({ lead_id, channel }), (res) => `${lead_id}: ${res.message}`),

  markReply: async (lead_id, intent) =>
    get()._act(() => api.markReply({ lead_id, intent }), (res) => `${lead_id}: ${res.message}`),

  markStatus: async (lead_id, status) =>
    get()._act(() => api.markStatus({ lead_id, status }), (res) => `${lead_id}: ${res.message}`),

  // Shared shape for one-click tracker actions: surface failures in the toast
  // instead of leaving an unhandled rejection and a silently unchanged table.
  _act: async (call, message) => {
    set({ error: "" });
    try {
      const res = await call();
      set({ toast: message(res) });
      await get().refresh();
      return res;
    } catch (e) {
      set({ error: e.message });
    }
  },
}));
