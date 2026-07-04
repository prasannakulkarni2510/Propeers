import { useLeads } from "../hooks/useLeads";
import ApprovalQueue from "../components/ApprovalQueue.jsx";
import UnmatchedReplies from "../components/UnmatchedReplies.jsx";

export default function Approvals() {
  const { leads, loading } = useLeads();
  return (
    <div>
      <h1 className="page-title">Approvals</h1>
      <p className="page-sub">Human-in-the-loop · mark what you actually sent and heard back</p>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <ApprovalQueue leads={leads} />
          <UnmatchedReplies />
        </>
      )}
    </div>
  );
}
