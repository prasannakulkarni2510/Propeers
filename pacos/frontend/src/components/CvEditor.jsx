import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { useStore } from "../store";

const ACCEPT = ".pdf,.docx,.txt,.md";

// The base CV is the grounding context for every generated asset. While the
// shipped sample file is still in place the model has nothing real to cite,
// which is exactly when assets start inventing facts - so this editor leads
// with a loud warning until a real CV is saved.
//
// The operator can paste text or upload a PDF/DOCX. An upload only fills the
// editor with the extracted text; nothing is saved until they review it and
// click Save, the same propose-then-confirm rule the extractors follow.
export default function CvEditor() {
  const setToast = useStore((s) => s.setToast);
  const setCvIsSample = useStore((s) => s.setCvIsSample);
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState("");
  const [saved, setSaved] = useState(""); // last saved text, so Cancel can revert
  const [isSample, setIsSample] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [fromFile, setFromFile] = useState("");
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  useEffect(() => {
    api
      .getCv()
      .then((res) => {
        setContent(res.content);
        setSaved(res.content);
        setIsSample(res.is_sample);
        setCvIsSample(res.is_sample || !res.content.trim());
        setLoaded(true);
      })
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const readFile = async (file) => {
    if (!file) return;
    setOpen(true);
    setReading(true);
    setError("");
    try {
      const res = await api.extractCv(file);
      setContent(res.content);
      setFromFile(file.name);
    } catch (e) {
      setError(e.message);
    } finally {
      setReading(false);
      if (fileRef.current) fileRef.current.value = ""; // allow re-picking the same file
    }
  };

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.saveCv(content);
      setIsSample(res.is_sample);
      setCvIsSample(res.is_sample);
      setSaved(res.content);
      setFromFile("");
      setToast("CV saved. New assets will be grounded in it.");
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const cancel = () => {
    setContent(saved);
    setFromFile("");
    setError("");
    setOpen(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    readFile(e.dataTransfer.files?.[0]);
  };
  const dropProps = {
    onDragOver: (e) => { e.preventDefault(); setDragging(true); },
    onDragLeave: () => setDragging(false),
    onDrop,
  };

  const needsCv = loaded && (isSample || !saved.trim());
  const words = content.trim() ? content.trim().split(/\s+/).length : 0;

  const fileInput = (
    <input
      ref={fileRef}
      type="file"
      accept={ACCEPT}
      hidden
      onChange={(e) => readFile(e.target.files?.[0])}
    />
  );

  return (
    <>
      {fileInput}
      {needsCv && (
        <div className="banner">
          Your CV is still the sample placeholder. Generated assets have no real
          facts to use, so they will invent experience and numbers. Upload or
          paste your real CV before generating.
        </div>
      )}
      {!open ? (
        <div className={`cv-strip ${dragging ? "dragging" : ""}`} {...dropProps}>
          <button
            className={`btn ${needsCv ? "btn-accent" : ""}`}
            onClick={() => fileRef.current?.click()}
          >
            {needsCv ? "Upload my CV" : "Replace CV file"}
          </button>
          <button className="btn btn-ghost" onClick={() => setOpen(true)}>
            {needsCv ? "Paste text instead" : "Edit CV text"}
          </button>
          <span className="muted">PDF, DOCX, or TXT. Or drop the file here.</span>
        </div>
      ) : (
        <div className={`panel ${dragging ? "dragging" : ""}`} {...dropProps}>
          <h3>My CV (grounding for generated assets)</h3>
          <p className="muted">
            Everything the model may claim about you must be in here: skills,
            projects, real numbers. A few hundred words is plenty.
          </p>
          {fromFile && (
            <p className="cv-note">
              Extracted from <b>{fromFile}</b>. PDF layouts don't always survive
              (columns, headers), so skim it and fix anything garbled before saving.
            </p>
          )}
          <textarea
            className="textarea"
            rows={14}
            placeholder="Paste your CV text here, or upload / drop a PDF or DOCX…"
            value={reading ? "Reading file…" : content}
            disabled={reading}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="btn-row">
            <button
              className="btn btn-accent"
              disabled={busy || reading || !content.trim()}
              onClick={save}
            >
              {busy ? "Saving…" : "Save CV"}
            </button>
            <button
              className="btn"
              disabled={busy || reading}
              onClick={() => fileRef.current?.click()}
            >
              {reading ? "Reading…" : "Upload PDF / DOCX"}
            </button>
            <button className="btn btn-ghost" disabled={busy} onClick={cancel}>
              Cancel
            </button>
            <span className="muted" style={{ marginLeft: "auto" }}>
              {words} word{words === 1 ? "" : "s"}
            </span>
          </div>
        </div>
      )}
      {error && <p className="jd-error">{error}</p>}
    </>
  );
}
