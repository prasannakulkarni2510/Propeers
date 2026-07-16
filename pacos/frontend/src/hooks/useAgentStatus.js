import { useEffect } from "react";
import { create } from "zustand";
import { api } from "../services/api";

// Module-level store for polled agent status. Because it lives outside the React
// tree, the data survives route/tab changes — switching pages never wipes it.
const agentStore = create((set) => ({
  agents: [],
  setAgents: (agents) => set({ agents }),
}));

// Mount ONCE, high in the tree (App), so the poll keeps running no matter which
// page is on screen. Generation runs on the backend; this keeps the board live
// even while the user is looking at another tab.
export function useAgentPolling(intervalMs = 3000) {
  const setAgents = agentStore((s) => s.setAgents);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const a = await api.agents();
        if (alive) setAgents(a);
      } catch (_) {}
    };
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [intervalMs, setAgents]);
}

// Read-only subscription for components that just display the board.
export function useAgentStatus() {
  return agentStore((s) => s.agents);
}
