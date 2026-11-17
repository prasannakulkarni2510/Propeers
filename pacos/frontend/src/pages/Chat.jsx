import { useEffect, useRef, useState } from "react";
import Icon from "../components/Icon.jsx";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useStore } from "../store";
import { useChat } from "../store/chat";
import LeadFieldsEditor, { EMPTY_LEAD, canSubmitLead } from "../components/LeadFieldsEditor.jsx";
import { ChangeCard, RecordCard } from "../components/ChatLeadCards.jsx";
import { MAX_IMAGES, imageFiles, prepareImage } from "../lib/images";

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
      <div className="proposal-title">New person{added && ", added"}</div>
      {!added && warnings.length > 0 && (
        <ul className="jd-warnings">
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
      {added ? (
        <p className="muted">
          {fields.full_name}, {fields.company_name}, is in your pipeline.
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
              {busy ? "Adding…" : "Add person"}
            </button>
            {fields.company_name.trim() && (
              <Link
                className="btn btn-ghost btn-sm"
                to={`/find?${new URLSearchParams({
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
  const words = draft.text.trim().split(/\s+/).length;
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
          Draft {DRAFT_LABEL[draft.asset] || draft.asset}, {words} words
        </span>
        <button className="btn btn-ghost btn-sm" onClick={copy}>Copy</button>
      </div>
      <pre className="draft-text">{draft.text}</pre>
      <p className="muted draft-note">Read it before you send it. PACOS never sends anything.</p>
    </div>
  );
}

const EXAMPLES = [
  "Who should I follow up with this week?",
  "Priya from Razorpay replied, she’s interested",
  "Draft a short LinkedIn DM to an ML engineering manager at Swiggy",
  "Add Priya Shah, engineering manager at Razorpay, Bengaluru",
];

export default function Chat() {
  const { messages, input, attachments, chatId, loading, pending, setInput, setAttachments, patch } = useChat();
  const busy = !!pending[chatId || "new"];
  const setToast = useStore((s) => s.setToast);
  const fileRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const endRef = useRef(null);
  const navigate = useNavigate();
  const { chatId: routeId } = useParams();

  // The address picks the chat: /c/<id> is a saved one, / is a new one. An
  // unsaved conversation at / is left alone when the page is revisited.
  useEffect(() => {
    const chat = useChat.getState();
    if (routeId) {
      chat.open(routeId).then((found) => {
        if (!found) navigate("/", { replace: true });
      });
    } else if (chat.chatId) {
      chat.startNew();
    }
  }, [routeId, navigate]);

  const send = () => useChat.getState().send((id) => navigate(`/c/${id}`, { replace: true }));
  const newChat = () => {
    useChat.getState().startNew();
    navigate("/");
  };

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
      <div className="chat-top">
        {(messages.length > 0 || chatId) && (
          <button className="btn btn-ghost btn-sm" onClick={newChat}>
            <Icon name="plus" size={14} /> New chat
          </button>
        )}
      </div>
      <div className="chat-scroll">
        {loading && <p className="muted chat-loading">Opening chat…</p>}
        {messages.length === 0 && !loading && (
          <div className="chat-hero">
            <h1>Who are we writing to today?</h1>
            <p>
              Tell me what happened, ask where things stand with someone, or paste a job description.
              I draft and keep track. You send.
            </p>
            <div className="chat-examples">
              {EXAMPLES.map((ex) => (
                <button key={ex} className="chat-example" onClick={() => setInput(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {(m.content || !(m.images?.length || m.imageCount)) && <div className="chat-bubble">{m.content}</div>}
            {m.images?.length > 0 && (
              <div className="chat-images">
                {m.images.map((src, k) => (
                  <img key={k} src={src} alt={`Attached image ${k + 1}`} />
                ))}
              </div>
            )}
            {!m.images?.length && m.imageCount > 0 && (
              <p className="muted chat-image-note">
                {m.imageCount === 1 ? "1 screenshot" : `${m.imageCount} screenshots`}, read once and not kept.
              </p>
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
                onAdded={() => patch(i, () => ({ added: true }))}
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
                <Icon name="close" size={12} />
              </button>
            </div>
          ))}
          <span className="muted">Read once, never stored.</span>
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
          className="icon-btn"
          title="Attach a screenshot (or paste or drop one)"
          aria-label="Attach image"
          disabled={busy || attachments.length >= MAX_IMAGES}
          onClick={() => fileRef.current?.click()}
        >
          <Icon name="image" size={18} />
        </button>
        <textarea
          className="textarea chat-input"
          rows={1}
          aria-label="Message"
          placeholder="Message PACOS, or paste a screenshot"
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
