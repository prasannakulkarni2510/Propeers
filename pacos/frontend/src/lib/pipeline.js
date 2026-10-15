// Derived pipeline views shared by the sidebar badges, Dashboard, Approvals,
// and Tracker so they all agree on what "ready" and "overdue" mean.

const todayIso = () => new Date().toISOString().slice(0, 10);

// Assets built, nothing sent yet: the operator's send queue.
export const isReadyToSend = (l) =>
  l.assets_generated === "true" && (l.status === "" || l.status === "pending");

export const isAwaitingReply = (l) => l.status === "sent";

// follow_up_due is an ISO date (YYYY-MM-DD), so string comparison is date order.
export const isFollowUpDue = (l) =>
  isAwaitingReply(l) && !!l.follow_up_due && l.follow_up_due <= todayIso();

export const isPerson = (l) => (l.lead_type || "person") !== "job";

export function pipelineCounts(leads) {
  let ready = 0, awaiting = 0, due = 0, needAssets = 0;
  for (const l of leads) {
    if (isReadyToSend(l)) ready++;
    if (isAwaitingReply(l)) awaiting++;
    if (isFollowUpDue(l)) due++;
    if (isPerson(l) && l.assets_generated !== "true") needAssets++;
  }
  return { ready, awaiting, due, needAssets };
}
