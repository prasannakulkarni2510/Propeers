// Global app state (Zustand). Holds the leads and the async actions
// that talk to the backend and keep everything in sync.
import { create } from "zustand";
import { api } from "../services/api";

export const useStore = create((set, get) => ({
  leads: [],
  loading: false,
  generating: false, // global so the "Generating…" state survives tab switches
  error: "",
  toast: "",
  cvIsSample: null, // null until CvEditor has loaded it

  setToast: (toast) => set({ toast }),
  clearToast: () => set({ toast: "" }),
  clearError: () => set({ error: "" }),
  setCvIsSample: (cvIsSample) => set({ cvIsSample }),

  refresh: async () => {
    set({ loading: true, error: "" });
    try {
      const leads = await api.leads();
      set({ leads, loading: false });
    } catch (e) {
      set({ error: e.message, loading: false });
    }
  },

  generate: async ({ lead_id = null, limit = 0 } = {}) => {
    if (get().generating) return; // guard against double-clicks / re-entry
    set({ error: "", generating: true });
    try {
      const res = await api.generate({ dry_run: false, limit, lead_id, review_hooks: false, only_missing: true });
      if (res.requested === 0) {
        set({ toast: "Every lead already has drafts." });
      } else {
        set({ toast: `Wrote drafts for ${res.generated} of ${res.requested} lead${res.requested === 1 ? "" : "s"}.` });
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

  markSent: async (lead_id, channel) =>
    get()._act(() => api.markSent({ lead_id, channel }), (res) => res.message),

  markReply: async (lead_id, intent) =>
    get()._act(() => api.markReply({ lead_id, intent }), (res) => res.message),

  // A change confirmed on a chat card. Resolves to the lead's new card, or
  // undefined on failure (shown in the toast).
  applyChatChange: async (change) =>
    get()._act(() => api.applyChatChange(change), (res) => `${res.full_name || res.lead_id}: saved.`),

  markStatus: async (lead_id, status) =>
    get()._act(() => api.markStatus({ lead_id, status }), (res) => res.message),

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
