import { useAgentStatus } from "../hooks/useAgentStatus";

// Live agent status board (docx: AgentStatus.jsx). Polls the backend.
export default function AgentStatus() {
  const agents = useAgentStatus();
  return (
    <div className="panel">
      <h3>Agent status</h3>
      <div className="agent-grid">
        {agents.map((a) => (
          <div className="agent" key={a.name}>
            <span className={`dot ${a.status}`} />
            <div>
              <div className="agent-name">{a.label}</div>
              <div className="agent-detail">{a.detail || a.status}</div>
            </div>
          </div>
        ))}
        {agents.length === 0 && <span className="muted">Loading agents…</span>}
      </div>
    </div>
  );
}
