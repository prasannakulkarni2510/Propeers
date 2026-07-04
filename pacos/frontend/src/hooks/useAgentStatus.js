import { useEffect } from "react";
import { useStore } from "../store";
import { api } from "../services/api";
import { create } from "zustand";

// Small local store just for polled agent status, so it can refresh on an
// interval without re-rendering the whole app tree.
const agentStore = create((set) => ({
  agents: [],
  setAgents: (agents) => set({ agents }),
}));

export function useAgentStatus(intervalMs = 4000) {
  const { agents, setAgents } = agentStore();
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
  return agents;
}
