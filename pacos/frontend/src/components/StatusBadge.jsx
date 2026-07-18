export default function StatusBadge({ status }) {
  const s = (status || "").trim();
  if (!s) return <span className="badge badge-empty">-</span>;
  return <span className={`badge badge-${s}`}>{s}</span>;
}
