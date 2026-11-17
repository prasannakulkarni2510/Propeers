// Derived pipeline views shared by the sidebar badges, the board and the
// lead panel so they all agree on what "ready" and "overdue" mean.

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

// Where a lead sits in the loop. Every lead lands in exactly one stage;
// outreach status wins over draft state once something has been sent.
export const LEAD_STAGES = [
  { id: "needs_assets", title: "To write", empty: "Everyone has messages written." },
  { id: "ready", title: "Ready to send", empty: "Nothing waiting to be sent." },
  { id: "awaiting", title: "Waiting for a reply", empty: "No one owes you a reply." },
  { id: "engaged", title: "Replied", empty: "No replies yet." },
  { id: "closed", title: "Finished", empty: "Nothing finished yet." },
];

const ENGAGED = new Set(["replied", "interested", "interview", "offer"]);

export function leadStage(l) {
  if (ENGAGED.has(l.status)) return "engaged";
  if (l.status === "rejected") return "closed";
  if (l.status === "sent") return "awaiting";
  if (l.assets_generated === "true") return "ready";
  return "needs_assets";
}
