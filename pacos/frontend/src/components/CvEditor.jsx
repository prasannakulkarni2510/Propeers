import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useStore } from "../store";

// The base CV is the grounding context for every generated asset. While the
// shipped sample file is still in place the model has nothing real to cite,
// which is exactly when assets start inventing facts - so this editor leads
// with a loud warning until a real CV is saved.
export default function CvEditor() {
  const setToast = useStore((s) => s.setToast);
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState("");
  const [isSample, setIsSample] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getCv()
      .then((res) => {
        setContent(res.content);
        setIsSample(res.is_sample);
        setLoaded(true);
      })
      .catch((e) => setError(e.message));
  }, []);

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.saveCv(content);
      setIsSample(res.is_sample);
      setToast("CV saved. New assets will be grounded in it.");
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const needsCv = loaded && (isSample || !content.trim());

  return (
    <>
      {needsCv && (
        <div className="banner">
          Your CV is still the sample placeholder. Generated assets have no real
          facts to use, so they will invent experience and numbers. Paste your
          real CV below before generating.
        </div>
      )}
      {!open ? (
        <div style={{ marginBottom: 16 }}>
          <button className={`btn ${needsCv ? "btn-accent" : ""}`} onClick={() => setOpen(true)}>
            {needsCv ? "Paste my CV" : "Edit my CV"}
          </button>
        </div>
      ) : (
        <div className="panel">
          <h3>My CV (grounding for generated assets)</h3>
          <p className="muted">
            Plain text. Everything the model may claim about you must be in
            here: skills, projects, real numbers. A few hundred words is plenty.
          </p>
          <textarea
            className="textarea"
            rows={14}
            placeholder="Paste your CV text here..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <div className="btn-row">
            <button className="btn btn-accent" disabled={busy || !content.trim()} onClick={save}>
              {busy ? "Saving..." : "Save CV"}
            </button>
            <button className="btn btn-ghost" disabled={busy} onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {error && <p className="jd-error">{error}</p>}
    </>
  );
}
