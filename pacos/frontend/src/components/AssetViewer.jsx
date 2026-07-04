import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useStore } from "../store";

const LABELS = {
  "cold_email.txt": "Cold Email",
  "cold_dm.txt": "Cold DM",
  "cover_letter.txt": "Cover Letter",
  "cv_notes.txt": "CV Notes",
};

// Assets per lead (docx: AssetViewer.jsx). Read the four files; copy to clipboard.
export default function AssetViewer({ leadId }) {
  const [data, setData] = useState(null);
  const [active, setActive] = useState("cold_email.txt");
  const [error, setError] = useState("");
  const setToast = useStore((s) => s.setToast);

  useEffect(() => {
    if (!leadId) return;
    setData(null);
    setError("");
    api.assets(leadId).then(setData).catch((e) => setError(e.message));
  }, [leadId]);

  if (!leadId) return <p className="muted">Select a lead to view its assets.</p>;
  if (error) return <div className="banner">{error}</div>;
  if (!data) return <p className="muted">Loading assets…</p>;

  if (!data.generated) {
    return (
      <div className="banner">
        No assets generated yet for <b>{leadId}</b>. Run Generate on the Dashboard.
      </div>
    );
  }

  const current = data.files.find((f) => f.name === active) || data.files[0];
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(current.content);
      setToast(`Copied ${LABELS[current.name]} to clipboard`);
    } catch (_) {
      setToast("Copy failed — select and copy manually");
    }
  };

  return (
    <div className="asset-layout">
      <div className="asset-list">
        {data.files.map((f) => (
          <div
            key={f.name}
            className={`asset-item ${f.name === active ? "active" : ""}`}
            onClick={() => setActive(f.name)}
          >
            {LABELS[f.name] || f.name}
          </div>
        ))}
      </div>
      <div>
        <div className="copy-bar">
          <b>{LABELS[current.name]}</b>
          <button className="btn btn-sm btn-accent" onClick={copy}>Copy</button>
        </div>
        <div className="asset-body">{current.content || "(empty)"}</div>
      </div>
    </div>
  );
}
