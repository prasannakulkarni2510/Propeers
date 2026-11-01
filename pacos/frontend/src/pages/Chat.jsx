import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { create } from "zustand";
import { api } from "../services/api";
import { useStore } from "../store";
import LeadFieldsEditor, { EMPTY_LEAD, canSubmitLead } from "../components/LeadFieldsEditor.jsx";
import { ChangeCard, RecordCard } from "../components/ChatLeadCards.jsx";
import { MAX_IMAGES, imageFiles, prepareImage } from "../lib/images";

const READ_LABEL = "[Attached screenshot, as read by the vision model]";

// What a past message says to the server. Images are sent once, with the
// message they're attached to; afterwards their text stands in for them.
// Server limit per message (backend/models.py ChatMessage.content). A long
// paste plus the text read from its screenshot can exceed it, which would
// make every later turn fail; the image text is kept, the typed text trimmed.
const MAX_CONTENT = 20000;

const forServer = (m) => {
  if (!m.imageText) return { role: m.role, content: m.content.slice(0, MAX_CONTENT) };
  const read = `${READ_LABEL}\n${m.imageText}`.slice(0, MAX_CONTENT);
  const room = MAX_CONTENT - read.length - 2;
  const typed = room > 0 ? m.content.slice(0, room) : "";
  return { role: m.role, content: [typed, read].filter(Boolean).join("\n\n") };
};

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
  // {role, content, images?, imageText?, proposal?, warnings?, draft?,
  //  records?, change?, changeState?, changeResult?, removed?: lead_id[]}
  messages: [],
  input: "",
  attachments: [], // data: URLs waiting to be sent with the next message
  busy: false,
  setMessages: (messages) => set({ messages }),
  setInput: (input) => set({ input }),
  setAttachments: (attachments) => set({ attachments }),
  setBusy: (busy) => set({ busy }),
}));

const EXAMPLES = [
  "Where am I with Abhishek Gupta?",
  "Abhishek Gupta from ABB rejected me for the AI Engineer role",
  "Add this person: Priya Shah, engineering manager at Razorpay, Bengaluru, priya@razorpay.com",
  "Who should I follow up with this week?",
  "Write an email to the data team at Razorpay asking for a data science internship",
  "Draft a short LinkedIn DM to an ML engineering manager at Swiggy",
];

export default function Chat() {
  const { messages, input, attachments, busy, setMessages, setInput, setAttachments, setBusy } = useChat();
  const setToast = useStore((s) => s.setToast);
  const fileRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const endRef = useRef(null);
  // Card actions write into the stored message so the outcome survives
  // leaving the page, like "added ✓" on lead proposals.
  const patch = (i, fn) =>
    setMessages(useChat.getState().messages.map((x, j) => (j === i ? { ...x, ...fn(x) } : x)));

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const attach = async (files) => {
    const imgs = imageFiles(files);
    if (!imgs.length) return;
    const room = MAX_IMAGES - useChat.getState().attachments.length;
    if (room <= 0 || imgs.length > room) {
      setToast(`Up to ${MAX_IMAGES} images per message.`);
    }
    for (const f of imgs.slice(0, Math.max(0, room))) {
      try {
        const url = await prepareImage(f);
        setAttachments([...useChat.getState().attachments, url]);
      } catch (e) {
        setToast(e.message);
      }
    }
  };

  const send = async () => {
    const content = input.trim();
    if ((!content && !attachments.length) || busy) return;
    const mine = { role: "user", content, images: attachments };
    const history = [...messages, mine];
    setMessages(history);
    setInput("");
    setAttachments([]);
    setBusy(true);
    try {
      const body = history
        .map((m, i) => (i === history.length - 1 ? { role: m.role, content, images: m.images } : forServer(m)))
        .filter((m) => m.content || m.images?.length);
      const res = await api.chat(body);
      setMessages([
        ...history.slice(0, -1),
        { ...mine, imageText: res.image_text || "" },
        {
          role: "assistant",
          content: res.reply,
          proposal: res.lead_proposal,
          warnings: res.warnings || [],
          draft: res.draft,
          records: res.records || [],
          change: res.change,
        },
      ]);
    } catch (e) {
      setMessages([...history, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={`chat-page ${dragging ? "chat-dragging" : ""}`}
      onDragOver={(e) => {
        if (![...e.dataTransfer.types].includes("Files")) return;
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
      }}
      onDrop={(e) => {
        if (!e.dataTransfer.files?.length) return;
        e.preventDefault();
        setDragging(false);
        attach(e.dataTransfer.files);
      }}
    >
      <div className="page-head">
        <h1 className="page-title">Chat</h1>
        <div className="btn-row">
          {messages.length > 0 && (
            <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => setMessages([])}>
              New chat
            </button>
          )}
          <Link className="btn btn-accent btn-sm" to="/dashboard">Dashboard</Link>
        </div>
      </div>
      <p className="page-sub">
        Ask where you stand with anyone in your leads, tracker, assets or
        replies, tell me what happened ("Priya replied, interested") and I'll
        propose the update, ask me to write an email, LinkedIn DM, or cover
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
            {(m.content || !m.images?.length) && <div className="chat-bubble">{m.content}</div>}
            {m.images?.length > 0 && (
              <div className="chat-images">
                {m.images.map((src, k) => (
                  <img key={k} src={src} alt={`Attached image ${k + 1}`} />
                ))}
              </div>
            )}
            {m.imageText && (
              <details className="chat-read">
                <summary>Text read from the image</summary>
                <pre>{m.imageText}</pre>
              </details>
            )}
            {m.change && (
              <ChangeCard
                change={m.change}
                state={m.changeState}
                result={m.changeResult}
                onDone={(changeState, changeResult) => patch(i, () => ({ changeState, changeResult }))}
              />
            )}
            {m.records?.length > 0 && (
              <div className="record-list">
                {m.records.map((r) => (
                  <RecordCard
                    key={r.lead_id}
                    rec={r}
                    removed={m.removed?.includes(r.lead_id)}
                    onRemoved={() => patch(i, (x) => ({ removed: [...(x.removed || []), r.lead_id] }))}
                  />
                ))}
              </div>
            )}
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
            <div className="chat-bubble muted">
              {messages[messages.length - 1]?.images?.length ? "Reading the image…" : "Thinking…"}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      {attachments.length > 0 && (
        <div className="chat-attachments">
          {attachments.map((src, k) => (
            <div key={k} className="chat-attachment">
              <img src={src} alt={`Image ${k + 1} to send`} />
              <button
                aria-label={`Remove image ${k + 1}`}
                onClick={() => setAttachments(attachments.filter((_, j) => j !== k))}
              >
                ✕
              </button>
            </div>
          ))}
          <span className="muted">Read once to fill in your message, never stored.</span>
        </div>
      )}
      <div className="chat-input-row">
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          multiple
          hidden
          onChange={(e) => {
            attach(e.target.files);
            e.target.value = "";
          }}
        />
        <button
          className="btn btn-ghost chat-attach"
          title="Attach a screenshot (or paste / drop one)"
          aria-label="Attach image"
          disabled={busy || attachments.length >= MAX_IMAGES}
          onClick={() => fileRef.current?.click()}
        >
          🖼
        </button>
        <textarea
          className="textarea chat-input"
          rows={2}
          placeholder="Message the PACOS assistant, or paste a screenshot… (Enter to send, Shift+Enter for newline)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPaste={(e) => {
            // Word/Excel/Outlook put a picture of the text on the clipboard
            // next to the text itself; then the text is what was meant.
            const types = [...(e.clipboardData?.types || [])];
            const hasText = types.includes("text/plain") || types.includes("text/html");
            if (!hasText && imageFiles(e.clipboardData?.files).length) {
              e.preventDefault();
              attach(e.clipboardData.files);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button
          className="btn btn-accent"
          disabled={busy || (!input.trim() && !attachments.length)}
          onClick={send}
        >
          Send
        </button>
      </div>
    </div>
  );
}
