import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { create } from "zustand";
import { api } from "../services/api";
import { useStore } from "../store";
import LeadFieldsEditor, { EMPTY_LEAD, canSubmitLead } from "../components/LeadFieldsEditor.jsx";

// A lead the assistant proposed mid-chat. Editable; nothing is written until
// the operator clicks Add (which uses the same POST /api/leads as the forms).
function ProposalCard({ proposal, warnings, added, onAdded }) {
  const addLead = useStore((s) => s.addLead);
  const { persona_tag, ...rest } = proposal;
  const [fields, setFields] = useState({ ...EMPTY_LEAD, ...rest });
  const [persona, setPersona] = useState(persona_tag || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      await addLead({ ...fields, persona_tag: persona });
      onAdded();
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

const DRAFT_LABEL = { cold_email: "Cold email", cold_dm: "LinkedIn DM", cover_letter: "Cover letter" };

// A piece of outreach the operator asked for in chat. Written with the same
// rules, playbook and CV as pipeline assets; copy it out, nothing is sent.
function DraftCard({ draft }) {
  const setToast = useStore((s) => s.setToast);
  const words = draft.text.trim().split(/s+/).length;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(draft.text);
      setToast("Draft copied.");
    } catch {
      setToast("Couldn't copy automatically. Select the text and copy it.");
    }
  };
  return (
    <div className="proposal-card draft-card">
      <div className="draft-head">
        <span className="proposal-title">
          Draft {DRAFT_LABEL[draft.asset] || draft.asset} · {words} words
        </span>
        <button className="btn btn-ghost btn-sm" onClick={copy}>Copy</button>
      </div>
      <pre className="draft-text">{draft.text}</pre>
      <p className="muted draft-note">Review and edit before sending. PACOS never sends anything.</p>
    </div>
  );
}

// Module-level so the conversation (and an in-flight reply) survives leaving
// the page and coming back. Cleared only by "New chat" or a reload.
const useChat = create((set) => ({
  messages: [], // {role, content, proposal?, warnings?, draft?}
  input: "",
  busy: false,
  setMessages: (messages) => set({ messages }),
  setInput: (input) => set({ input }),
  setBusy: (busy) => set({ busy }),
}));

const EXAMPLES = [
  "Add this person: Priya Shah, engineering manager at Razorpay, Bengaluru, priya@razorpay.com",
  "Who should I follow up with this week?",
  "Write an email to the data team at Razorpay asking for a data science internship",
  "Draft a short LinkedIn DM to an ML engineering manager at Swiggy",
];

export default function Chat() {
  const { messages, input, busy, setMessages, setInput, setBusy } = useChat();
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
          draft: res.draft,
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
      <div className="page-head">
        <h1 className="page-title">Chat</h1>
        {messages.length > 0 && (
          <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => setMessages([])}>
            New chat
          </button>
        )}
      </div>
      <p className="page-sub">
        Ask about your pipeline, ask me to write an email, LinkedIn DM, or cover
        letter, or describe a person/JD and I'll propose a lead you can approve
        into leads.csv.
      </p>
      <div className="chat-scroll">
        {messages.length === 0 && (
          <div className="chat-examples">
            <span className="muted">Try one, or paste a whole JD:</span>
            {EXAMPLES.map((ex) => (
              <button key={ex} className="chat-example" onClick={() => setInput(ex)}>
                {ex}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="chat-bubble">{m.content}</div>
            {m.draft && <DraftCard draft={m.draft} />}
            {m.proposal && (
              <ProposalCard
                proposal={m.proposal}
                warnings={m.warnings || []}
                added={!!m.added}
                onAdded={() =>
                  setMessages(
                    useChat.getState().messages.map((x, j) => (j === i ? { ...x, added: true } : x)),
                  )
                }
              />
            )}
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
