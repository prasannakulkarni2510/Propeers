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
export default function CvEditor({ open, setOpen }) {
  const setToast = useStore((s) => s.setToast);
  const setCvIsSample = useStore((s) => s.setCvIsSample);
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
      setToast("CV saved. New drafts will use it.");
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
  const tempWords = tempCv.trim() ? tempCv.trim().split(/\s+/).length : 0;
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
      {needsCv && !open && (
        <div className="banner cv-strip">
          <span style={{ flex: "1 1 320px" }}>
            PACOS is still using a sample CV, so drafts would invent your experience. Add yours first.
          </span>
          <button className="btn btn-accent btn-sm" onClick={() => fileRef.current?.click()}>Upload my CV</button>
          <button className="btn btn-sm" onClick={() => setOpen(true)}>Paste it</button>
        </div>
      )}
      {tempCv && !open && (
        <div className="cv-temp">
          <span>
            <b>Using a temporary CV</b> ({tempWords} words) in this tab only. It is never saved.
          </span>
          <button className="btn btn-ghost btn-sm" onClick={openTemp}>Edit</button>
          <button className="btn btn-ghost btn-sm" onClick={removeTemp}>Remove</button>
        </div>
      )}
      {open && (
        <div className={`panel ${dragging ? "dragging" : ""}`} {...dropProps}>
          <h3>{temp ? "CV for this tab only" : "My CV"}</h3>
          <p className="muted">
            {temp
              ? "Drafts written in this tab use this CV. It is never saved and disappears when you close the tab."
              : "Drafts can only claim what is written here: skills, projects, real numbers. A few hundred words is plenty."}
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
              {temp ? "Use for this tab" : busy ? "Saving…" : "Save CV"}
            </button>
            <button
              className="btn"
              disabled={busy || reading}
              onClick={() => fileRef.current?.click()}
            >
              {reading ? "Reading…" : "Upload PDF or DOCX"}
            </button>
            <button className="btn btn-ghost" disabled={busy} onClick={cancel}>
              Cancel
            </button>
            <span className="muted" style={{ marginLeft: "auto" }}>
              {words} word{words === 1 ? "" : "s"}
            </span>
          </div>
          {!temp && !tempCv && (
            <p className="muted" style={{ marginTop: 12, marginBottom: 0 }}>
              Trying PACOS with someone else’s login?{" "}
              <button className="authgate-trial-fill" onClick={openTemp}>Use your CV for this tab only</button>
              , it is never saved.
            </p>
          )}
        </div>
      )}
      {error && <p className="jd-error">{error}</p>}
    </>
  );
}
