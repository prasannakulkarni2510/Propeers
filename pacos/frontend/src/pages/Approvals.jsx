import { useLeads } from "../hooks/useLeads";
import ApprovalQueue from "../components/ApprovalQueue.jsx";
import UnmatchedReplies from "../components/UnmatchedReplies.jsx";

export default function Approvals() {
  const { leads, loading } = useLeads();
  return (
    <div>
      <h1 className="page-title">Approvals</h1>
      <p className="page-sub">Mark what you actually sent and what you heard back.</p>
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
