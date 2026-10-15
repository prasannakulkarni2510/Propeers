import { useEffect, useRef, useState } from "react";
import { api, sessionCv } from "../services/api";
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
//
// "This session only" mode keeps a visitor's own CV in this tab (sessionStorage)
// instead of saving it to the server: generation uses it, and the browser
// deletes it when the tab closes.
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
  const [mode, setMode] = useState("saved"); // which CV the open editor edits
  const [tempCv, setTempCv] = useState(() => sessionCv.get());

  useEffect(() => {
    api
      .getCv()
      .then((res) => {
        setContent(res.content);
        setSaved(res.content);
        setIsSample(res.is_sample);
        setCvIsSample((res.is_sample || !res.content.trim()) && !sessionCv.get());
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

  const openTemp = () => {
    setMode("temp");
    setContent(tempCv);
    setFromFile("");
    setError("");
    setOpen(true);
  };

  const useTemp = () => {
    sessionCv.set(content);
    setTempCv(content);
    setCvIsSample(false);
    setMode("saved");
    setContent(saved);
    setFromFile("");
    setToast("Temporary CV in use for this tab. It's deleted when you close the tab.");
    setOpen(false);
  };

  const removeTemp = () => {
    sessionCv.set("");
    setTempCv("");
    setCvIsSample(isSample || !saved.trim());
    setToast("Temporary CV removed. Generation uses the saved CV again.");
  };

  const save = async () => {
    if (mode === "temp") return useTemp();
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
    setMode("saved");
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

  const needsCv = loaded && (isSample || !saved.trim()) && !tempCv.trim();
  const tempWords = tempCv.trim() ? tempCv.trim().split(/s+/).length : 0;
  const temp = mode === "temp";
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
      {tempCv && !open && (
        <div className="cv-temp">
          <span>
            <b>Using your temporary CV</b> ({tempWords} words) for this tab. It is
            not saved anywhere and is deleted when you close the tab.
          </span>
          <button className="btn btn-ghost" onClick={openTemp}>Edit</button>
          <button className="btn btn-ghost" onClick={removeTemp}>Remove</button>
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
          {!tempCv && (
            <button className="btn btn-ghost" onClick={openTemp}>
              Use my own CV for this session
            </button>
          )}
          <span className="muted">PDF, DOCX, or TXT. Or drop the file here.</span>
        </div>
      ) : (
        <div className={`panel ${dragging ? "dragging" : ""}`} {...dropProps}>
          <h3>{temp ? "Temporary CV (this tab only)" : "My CV (grounding for generated assets)"}</h3>
          <p className="muted">
            {temp
              ? "Assets you generate in this tab will be grounded in this CV. It is never saved on the server and is deleted when you close the tab."
              : "Everything the model may claim about you must be in here: skills, projects, real numbers. A few hundred words is plenty."}
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
              {temp ? "Use for this session" : busy ? "Saving…" : "Save CV"}
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
