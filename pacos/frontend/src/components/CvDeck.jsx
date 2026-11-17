import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { api, sessionCv } from "../services/api";
import { useStore } from "../store";

const ACCEPT = ".pdf,.docx,.txt,.md";
const COLORS = ["coral", "amber", "sage", "sky", "plum", "slate"];
const COLOR_NAME = { coral: "Coral", amber: "Amber", sage: "Sage", sky: "Sky", plum: "Plum", slate: "Slate" };

// Deck geometry, in px. Each card shows its name strip above the next one.
const STEP = 50;
const CARD_H = 132;
const SPREAD = 64; // how far the cards below a lifted one move out of its way

const wordCount = (text) => (text.trim() ? text.trim().split(/\s+/).length : 0);
const addedOn = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
};
const nameFromFile = (filename) => filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim().slice(0, 80);

// Several CVs kept as a stack of cards; one is in use and grounds every
// message PACOS writes. Hovering a card lifts it out of the stack, clicking
// opens it beside the deck. Nothing is saved until Save.
//
// A visitor on someone else's login can instead keep their own CV in this tab
// only (sessionStorage): generation uses it and the browser deletes it when
// the tab closes.
export default function CvDeck() {
  const setToast = useStore((s) => s.setToast);
  const setCvIsSample = useStore((s) => s.setCvIsSample);
  const [cvs, setCvs] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [dealt, setDealt] = useState(false); // false until the cards fan out
  const [dealing, setDealing] = useState(true); // stagger only the first fan-out
  const [hov, setHov] = useState(null);
  const [openId, setOpenId] = useState(null); // a cv_id, "new", "temp" or null
  const [draft, setDraft] = useState({ name: "", content: "", color: "" });
  const [fromFile, setFromFile] = useState("");
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [tempCv, setTempCv] = useState(() => sessionCv.get());
  const fileRef = useRef(null);

  const apply = (rows, temp = tempCv) => {
    setCvs(rows);
    setCvIsSample(rows.length === 0 && !temp.trim());
  };

  useEffect(() => {
    let timer;
    api
      .cvs()
      .then((rows) => {
        apply(rows);
        setLoaded(true);
        // Two frames: the cards must be painted stacked before they fan out.
        requestAnimationFrame(() => requestAnimationFrame(() => setDealt(true)));
        timer = setTimeout(() => setDealing(false), 900);
      })
      .catch((e) => {
        setError(e.message);
        setLoaded(true);
      });
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The CV in use sits at the front of the stack, fully visible.
  const deck = [...cvs.filter((c) => !c.is_active), ...cvs.filter((c) => c.is_active)];
  const openIndex = deck.findIndex((c) => c.cv_id === openId);
  const lifted = hov ?? (openIndex >= 0 ? openIndex : null);
  const opened = openIndex >= 0 ? deck[openIndex] : null;
  const isTemp = openId === "temp";
  const isNew = openId === "new";

  const show = (id, next) => {
    setOpenId(id);
    setDraft(next);
    setFromFile("");
    setError("");
    setConfirmDelete(false);
  };
  const close = () => show(null, { name: "", content: "", color: "" });
  const openCard = (cv) => show(cv.cv_id, { name: cv.name, content: cv.content, color: cv.color || COLORS[0] });
  const openNew = (name = "", content = "") =>
    show("new", { name, content, color: COLORS[cvs.length % COLORS.length] });
  const openTemp = () => show("temp", { name: "", content: tempCv, color: "" });

  const readFile = async (file) => {
    if (!file) return;
    setReading(true);
    setError("");
    try {
      const res = await api.extractCv(file);
      if (openId) {
        setDraft((d) => ({ ...d, content: res.content, name: d.name || (isTemp ? "" : nameFromFile(file.name)) }));
      } else {
        openNew(nameFromFile(file.name), res.content);
      }
      setFromFile(file.name);
    } catch (e) {
      setError(e.message);
    } finally {
      setReading(false);
      if (fileRef.current) fileRef.current.value = ""; // allow re-picking the same file
    }
  };

  const run = async (work) => {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    if (isTemp) {
      sessionCv.set(draft.content);
      setTempCv(draft.content);
      setCvIsSample(false);
      setToast("Temporary CV in use for this tab. It's deleted when you close the tab.");
      return close();
    }
    return run(async () => {
      const body = { name: draft.name.trim() || "My CV", content: draft.content, color: draft.color };
      const row = isNew ? await api.createCv(body) : await api.updateCv(openId, body);
      apply(await api.cvs());
      setToast(row.is_active ? "CV saved. New messages will use it." : "CV saved.");
      close();
    });
  };

  const use = () =>
    run(async () => {
      await api.useCv(openId);
      apply(await api.cvs());
      setToast(`New messages will be written from “${opened.name}”.`);
    });

  const remove = () =>
    run(async () => {
      await api.deleteCv(openId);
      apply(await api.cvs());
      setToast("CV deleted.");
      close();
    });

  const removeTemp = () => {
    sessionCv.set("");
    setTempCv("");
    setCvIsSample(cvs.length === 0);
    setToast("Temporary CV removed. Messages use the saved CV again.");
    if (isTemp) close();
  };

  const dirty = opened
    ? draft.name !== opened.name || draft.content !== opened.content || draft.color !== (opened.color || COLORS[0])
    : true;
  const words = wordCount(draft.content);
  const mid = (deck.length - 1) / 2;
  const stackHeight = deck.length ? (deck.length - 1) * STEP + CARD_H + 48 : 0;

  const dropProps = {
    onDragOver: (e) => {
      if (![...e.dataTransfer.types].includes("Files")) return;
      e.preventDefault();
      setDragging(true);
    },
    onDragLeave: (e) => {
      if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
    },
    onDrop: (e) => {
      if (!e.dataTransfer.files?.length) return;
      e.preventDefault();
      setDragging(false);
      readFile(e.dataTransfer.files[0]);
    },
  };

  return (
    <div className={`cv-deck ${dragging ? "dragging" : ""}`} {...dropProps}>
      <input ref={fileRef} type="file" accept={ACCEPT} hidden onChange={(e) => readFile(e.target.files?.[0])} />

      <div className="cv-deck-side">
        {loaded && deck.length === 0 && !openId && (
          <div className="banner">
            PACOS is still using a sample CV, so messages would invent your experience. Add yours first.
          </div>
        )}
        <div className="cv-stack" style={{ height: stackHeight }} onMouseLeave={() => setHov(null)}>
          {deck.map((cv, i) => {
            let x = 0, y = i * STEP, r = (i - mid) * 1.1, s = 1;
            if (!dealt) {
              y = 0;
              r = 0;
            } else if (lifted !== null) {
              if (i === lifted) {
                x = 18;
                s = 1.04;
                r = 0;
              } else if (i > lifted) {
                y += SPREAD / (i - lifted + 0.4);
              }
            }
            const count = wordCount(cv.content);
            return (
              <button
                key={cv.cv_id}
                className={`cv-card ${cv.cv_id === openId ? "is-open" : ""}`}
                data-color={cv.color || COLORS[0]}
                aria-pressed={cv.cv_id === openId}
                style={{
                  transform: `translate(${x}px, ${y}px) rotate(${r}deg) scale(${s})`,
                  opacity: dealt ? 1 : 0,
                  zIndex: i === lifted ? 50 : i,
                  transitionDelay: dealing ? `${i * 55}ms` : "0ms",
                }}
                onMouseEnter={() => setHov(i)}
                onFocus={() => setHov(i)}
                onBlur={() => setHov(null)}
                onClick={() => (cv.cv_id === openId ? close() : openCard(cv))}
              >
                <span className="cv-card-strip">
                  <span className="cv-card-badge">CV</span>
                  <span className="cv-card-name">{cv.name}</span>
                  {cv.is_active && <span className="cv-card-used">In use</span>}
                </span>
                <span className="cv-card-sub">
                  {count} word{count === 1 ? "" : "s"}
                  {addedOn(cv.created_at) && `, added ${addedOn(cv.created_at)}`}
                </span>
                <span className="cv-card-bar" style={{ width: "72%" }} />
                <span className="cv-card-bar" style={{ width: "50%" }} />
              </button>
            );
          })}
        </div>
        <div className="btn-row">
          <button className="btn btn-accent" disabled={reading} onClick={() => fileRef.current?.click()}>
            <Icon name="plus" size={15} /> {reading && !openId ? "Reading…" : "Upload a CV"}
          </button>
          <button className="btn" onClick={() => openNew()}>Paste one</button>
        </div>
        <p className="muted cv-deck-hint">
          PDF, DOCX or text. You can also drop a file anywhere here.
          {deck.length > 1 && " The card marked In use is the one every message is written from."}
        </p>
        {tempCv ? (
          <div className="cv-temp">
            <span>
              <b>Using a temporary CV</b> ({wordCount(tempCv)} words) in this tab only. It is never saved.
            </span>
            <button className="btn btn-ghost btn-sm" onClick={openTemp}>Edit</button>
            <button className="btn btn-ghost btn-sm" onClick={removeTemp}>Remove</button>
          </div>
        ) : (
          <p className="muted">
            Trying PACOS with someone else’s login?{" "}
            <button className="authgate-trial-fill" onClick={openTemp}>Use your CV for this tab only</button>
            , it is never saved.
          </p>
        )}
        {error && !openId && <p className="jd-error">{error}</p>}
      </div>

      {openId ? (
        // Keyed so each card pops in afresh when another one is picked.
        <div className="panel cv-pop" key={openId} data-color={isTemp ? undefined : draft.color}>
          <div className="cv-pop-head">
            <h3>{isTemp ? "CV for this tab only" : isNew ? "New CV" : opened?.is_active ? "CV in use" : "Saved CV"}</h3>
            <button className="icon-btn" aria-label="Close" onClick={close}>
              <Icon name="close" size={16} />
            </button>
          </div>
          {isTemp ? (
            <p className="muted">
              Messages written in this tab use this CV. It is never saved and disappears when you close the tab.
            </p>
          ) : (
            <div className="cv-pop-meta">
              <label className="field">
                <span className="field-label">Name</span>
                <input
                  className="input"
                  maxLength={80}
                  placeholder="For example: Data roles"
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </label>
              <div className="field">
                <span className="field-label" id="cv-color-label">Card colour</span>
                <div className="cv-swatches" role="radiogroup" aria-labelledby="cv-color-label">
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      role="radio"
                      aria-checked={draft.color === c}
                      aria-label={COLOR_NAME[c]}
                      title={COLOR_NAME[c]}
                      className="cv-swatch"
                      data-color={c}
                      onClick={() => setDraft({ ...draft, color: c })}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          {fromFile && (
            <p className="cv-note">
              Extracted from <b>{fromFile}</b>. PDF layouts don’t always survive (columns, headers), so skim it and
              fix anything garbled before saving.
            </p>
          )}
          <textarea
            className="textarea"
            rows={14}
            aria-label="CV text"
            placeholder="Paste your CV text here, or upload a PDF or DOCX…"
            value={reading ? "Reading file…" : draft.content}
            disabled={reading}
            onChange={(e) => setDraft({ ...draft, content: e.target.value })}
          />
          <div className="btn-row">
            <button className="btn btn-accent" disabled={busy || reading || !draft.content.trim() || !dirty} onClick={save}>
              {isTemp ? "Use for this tab" : busy ? "Saving…" : isNew ? "Add to my CVs" : "Save changes"}
            </button>
            {opened && !opened.is_active && (
              <button className="btn" disabled={busy || reading || dirty} title={dirty ? "Save your changes first" : ""} onClick={use}>
                Use this CV
              </button>
            )}
            <button className="btn btn-ghost" disabled={busy || reading} onClick={() => fileRef.current?.click()}>
              {reading ? "Reading…" : "Replace from a file"}
            </button>
            <span className="muted cv-pop-words">
              {words} word{words === 1 ? "" : "s"}
            </span>
          </div>
          {opened && (
            <div className="cv-pop-foot">
              {confirmDelete ? (
                <>
                  <span className="muted">
                    Delete “{opened.name}”?{opened.is_active && cvs.length > 1 && " Another CV will be used instead."}
                  </span>
                  <button className="btn btn-sm btn-danger-quiet" disabled={busy} onClick={remove}>Yes, delete</button>
                  <button className="btn btn-sm btn-ghost" onClick={() => setConfirmDelete(false)}>Keep it</button>
                </>
              ) : (
                <button className="btn btn-sm btn-danger-quiet" onClick={() => setConfirmDelete(true)}>
                  <Icon name="trash" size={14} /> Delete this CV
                </button>
              )}
            </div>
          )}
          {error && <p className="jd-error">{error}</p>}
        </div>
      ) : (
        loaded && deck.length > 0 && (
          <div className="cv-deck-idle">
            <p>Pick a card to read it, change it, or switch to it.</p>
          </div>
        )
      )}
    </div>
  );
}
