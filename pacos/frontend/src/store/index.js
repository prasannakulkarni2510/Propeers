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
  error: "",
  toast: "",

  setToast: (toast) => set({ toast }),
  clearToast: () => set({ toast: "" }),

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

  generate: async ({ dry_run = false, limit = 0, lead_id = null, review_hooks = false } = {}) => {
    set({ error: "" });
    try {
      const res = await api.generate({ dry_run, limit, lead_id, review_hooks });
      const mode = res.dry_run ? "dry-run" : res.model;
      set({ toast: `Generated ${res.generated}/${res.requested} via ${mode}` });
      await get().refresh();
      return res;
    } catch (e) {
      set({ error: e.message });
      throw e;
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

  associate: async (reply_id, lead_id) => {
    const res = await api.associate({ reply_id, lead_id });
    set({ toast: res.message });
    await get().refresh();
  },

  markSent: async (lead_id, channel) => {
    const res = await api.markSent({ lead_id, channel });
    set({ toast: `${lead_id}: ${res.message}` });
    await get().refresh();
  },

  markReply: async (lead_id, intent) => {
    const res = await api.markReply({ lead_id, intent });
    set({ toast: `${lead_id}: ${res.message}` });
    await get().refresh();
  },

  markStatus: async (lead_id, status) => {
    const res = await api.markStatus({ lead_id, status });
    set({ toast: `${lead_id}: ${res.message}` });
    await get().refresh();
  },
}));
