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

// Where a lead sits in the overall loop, for the Leads board. Every lead lands
// in exactly one stage; outreach status wins over asset state once it's sent.
export const LEAD_STAGES = [
  { id: "needs_assets", title: "Needs assets", hint: "Generate outreach from the Dashboard." },
  { id: "ready", title: "Ready to send", hint: "Drafts built. Send by hand.", tone: "accent" },
  { id: "awaiting", title: "Awaiting reply", hint: "Sent. Chase on the follow-up date." },
  { id: "engaged", title: "Engaged", hint: "Replied, interested, interviewing or offer.", tone: "ok" },
  { id: "closed", title: "Closed", hint: "Rejected." },
];

const ENGAGED = new Set(["replied", "interested", "interview", "offer"]);

export function leadStage(l) {
  if (ENGAGED.has(l.status)) return "engaged";
  if (l.status === "rejected") return "closed";
  if (l.status === "sent") return "awaiting";
  if (l.assets_generated === "true") return "ready";
  return "needs_assets";
}
