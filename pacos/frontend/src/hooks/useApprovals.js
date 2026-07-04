import { useStore } from "../store";

// Thin wrapper exposing the approval actions to components.
export function useApprovals() {
  const { markSent, markReply, markStatus } = useStore();
  return { markSent, markReply, markStatus };
}
