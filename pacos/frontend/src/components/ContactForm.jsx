import { useEffect, useState } from "react";
import { api } from "../services/api";

// Where the visitor came from (?ref=linkedin on a shared link). Read once when
// the app loads and kept for the tab, because the address loses it as soon as
// the visitor moves between pages.
const REF_KEY = "pacos_ref";
try {
  const ref = new URLSearchParams(window.location.search).get("ref");
  if (ref) sessionStorage.setItem(REF_KEY, ref.slice(0, 60));
} catch { /* storage blocked: the row just has no ref */ }
const currentRef = () => {
  try { return sessionStorage.getItem(REF_KEY) || ""; } catch { return ""; }
};

const EMPTY = { name: "", email: "", company: "", message: "", website: "" };

// A short "leave your details" form for visitors. Each submission becomes a
// row in a Google Sheet (backend/routes/contact.py). Renders nothing unless
// the server has a sheet configured. `collapsed` starts it as a single link.
export default function ContactForm({ page, collapsed = false, title = "Leave your details" }) {
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(!collapsed);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api.contactStatus().then((s) => setEnabled(!!s.enabled)).catch(() => {});
  }, []);

  if (!enabled) return null;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.contact({ ...form, ref: currentRef(), page });
      setSent(true);
      setForm(EMPTY);
    } catch (err) {
      setError(err.message || "Couldn't send. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button type="button" className="contact-toggle" onClick={() => setOpen(true)}>
        Hiring, or want to talk? Leave your details
      </button>
    );
  }

  if (sent) {
    return (
      <div className="panel contact-card" role="status">
        <h2 className="contact-title">Thanks, got it</h2>
        <p className="muted">I’ll get back to you by email.</p>
      </div>
    );
  }

  return (
    <form className="panel contact-card" onSubmit={submit}>
      <h2 className="contact-title">{title}</h2>
      <label className="field">
        <span className="field-label">Name</span>
        <input className="input" value={form.name} onChange={set("name")} maxLength={120} autoComplete="name" required />
      </label>
      <label className="field">
        <span className="field-label">Email</span>
        <input className="input" type="email" value={form.email} onChange={set("email")} maxLength={200} autoComplete="email" required />
      </label>
      <label className="field">
        <span className="field-label">Company <span className="muted">(optional)</span></span>
        <input className="input" value={form.company} onChange={set("company")} maxLength={160} autoComplete="organization" />
      </label>
      <label className="field">
        <span className="field-label">Message <span className="muted">(optional)</span></span>
        <textarea className="textarea" rows={3} value={form.message} onChange={set("message")} maxLength={1000} />
      </label>
      {/* Honeypot: hidden from people, often filled in by bots. */}
      <input className="contact-hp" tabIndex={-1} autoComplete="off" aria-hidden="true" value={form.website} onChange={set("website")} />
      {error && <p className="jd-error" role="alert">{error}</p>}
      <button className="btn btn-accent" type="submit" disabled={busy || !form.name.trim() || !form.email.trim()}>
        {busy ? "Sending…" : "Send"}
      </button>
      <p className="contact-note muted">Saved to a private sheet and used only to reply to you.</p>
    </form>
  );
}
