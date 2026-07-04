import { useEffect } from "react";
import { useStore } from "../store";

// Load leads + stats once on mount; expose the slice.
export function useLeads() {
  const { leads, stats, loading, error, refresh } = useStore();
  useEffect(() => {
    if (leads.length === 0) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { leads, stats, loading, error, refresh };
}
