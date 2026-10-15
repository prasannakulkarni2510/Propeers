import { useEffect } from "react";
import { useStore } from "../store";

// Load leads + stats once on mount; expose the slice. Several components mount
// this at once (the shell's nav badges plus the page), so skip the fetch when
// one is already in flight.
export function useLeads() {
  const { leads, stats, loading, error, refresh } = useStore();
  useEffect(() => {
    const s = useStore.getState();
    if (s.leads.length === 0 && !s.loading) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { leads, stats, loading, error, refresh };
}
