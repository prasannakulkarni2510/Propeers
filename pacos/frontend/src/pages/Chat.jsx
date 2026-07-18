import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { useStore } from "../store";
import LeadFieldsEditor, { EMPTY_LEAD, canSubmitLead } from "../components/LeadFieldsEditor.jsx";

// A lead the assistant proposed mid-chat. Editable; nothing is written until
// the operator clicks Add (which uses the same POST /api/leads as the forms).
function ProposalCard({ proposal, warnings }) {
  const addLead = useStore((s) => s.addLead);
  const { persona_tag, ...rest } = proposal;
  const [fields, setFields] = useState({ ...EMPTY_LEAD, ...rest });
  const [persona, setPersona] = useState(persona_tag || "");
  const [busy, setBusy] = useState(false);
  const [added, setAdded] = useState(false);
  const [error, setError] = useState("");

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      await addLead({ ...fields, persona_tag: persona });
      setAdded(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="proposal-card">
      <div className="proposal-title">Proposed lead {added && "· added ✓"}</div>
      {!added && warnings.length > 0 && (
        <ul className="jd-warnings">
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
      {added ? (
        <p className="muted">
          {fields.full_name} @ {fields.company_name} is in leads.csv.
        </p>
      ) : (
        <>
          <LeadFieldsEditor
            fields={fields}
            setFields={setFields}
            persona={persona}
            setPersona={setPersona}
          />
          <div className="btn-row">
            <button
              className="btn btn-accent btn-sm"
              disabled={busy || !canSubmitLead(fields, persona)}
              onClick={confirm}
            >
              {busy ? "Adding…" : "Add to leads.csv"}
            </button>
            {fields.company_name.trim() && (
              <Link
                className="btn btn-ghost btn-sm"
                to={`/discovery?${new URLSearchParams({
                  company: fields.company_name,
                  role: fields.job_title,
                  city: fields.city,
                })}`}
              >
                Find people at {fields.company_name}
              </Link>
            )}
          </div>
        </>
      )}
      {error && <p className="jd-error">{error}</p>}
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState([]); // {role, content, proposal?, warnings?}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async () => {
    const content = input.trim();
    if (!content || busy) return;
    const history = [...messages, { role: "user", content }];
    setMessages(history);
    setInput("");
    setBusy(true);
    try {
      const res = await api.chat(history.map(({ role, content }) => ({ role, content })));
      setMessages([
        ...history,
        {
          role: "assistant",
          content: res.reply,
          proposal: res.lead_proposal,
          warnings: res.warnings || [],
        },
      ]);
    } catch (e) {
      setMessages([...history, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="chat-page">
      <h1 className="page-title">Chat</h1>
      <p className="page-sub">
        Ask about your pipeline, draft outreach, or describe a person/JD, and I'll
        propose a lead you can approve into leads.csv.
      </p>
      <div className="chat-scroll">
        {messages.length === 0 && (
          <p className="muted">
            Try: “Add this person: Priya Shah, engineering manager at Razorpay,
            Bengaluru, priya@razorpay.com”, or paste a whole JD.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="chat-bubble">{m.content}</div>
            {m.proposal && <ProposalCard proposal={m.proposal} warnings={m.warnings || []} />}
          </div>
        ))}
        {busy && (
          <div className="chat-msg assistant">
            <div className="chat-bubble muted">Thinking…</div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="chat-input-row">
        <textarea
          className="textarea chat-input"
          rows={2}
          placeholder="Message the PACOS assistant… (Enter to send, Shift+Enter for newline)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="btn btn-accent" disabled={busy || !input.trim()} onClick={send}>
          Send
        </button>
      </div>
    </div>
  );
}
