import { useEffect, useState } from "react";
import { api, authToken } from "../services/api";

// Gate for cloud deployments: when the backend has PACOS_AUTH_TOKEN set, every
// /api call needs the operator's token. We probe once with /api/stats — a 401
// shows this form; any other outcome (including backend-down) lets the app
// render normally so local/exe usage is untouched.
export default function AuthGate({ children }) {
  const [state, setState] = useState("checking"); // checking | locked | ok
  const [token, setToken] = useState("");
  const [error, setError] = useState("");

  const probe = async () => {
    try {
      await api.stats();
      setState("ok");
    } catch (e) {
      setState(e.status === 401 ? "locked" : "ok");
    }
  };

  useEffect(() => {
    probe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const unlock = async (e) => {
    e.preventDefault();
    const t = token.trim();
    if (!/^[\x21-\x7E]+$/.test(t)) {
      setError(
        "That looks like the masked •••• value, not the token itself. " +
        "In Render, click the eye icon next to PACOS_AUTH_TOKEN to reveal " +
        "the real text, copy that, and paste it here."
      );
      return;
    }
    authToken.set(t);
    setError("");
    try {
      await api.stats();
      setState("ok");
    } catch (err) {
      if (err.status === 401) {
        authToken.set("");
        setError("That token was rejected — check PACOS_AUTH_TOKEN.");
      } else {
        setState("ok"); // backend trouble ≠ bad token; let the app surface it
      }
    }
  };

  if (state === "checking") return <div className="authgate"><p className="muted">Connecting…</p></div>;
  if (state === "ok") return children;
  return (
    <div className="authgate">
      <form className="panel authgate-card" onSubmit={unlock}>
        <div className="brand">
          PAC<span className="brand-accent">OS</span>
        </div>
        <p className="muted">
          This deployment is protected. Paste your access token
          (the PACOS_AUTH_TOKEN you configured on the server).
        </p>
        <input
          className="input"
          type="password"
          placeholder="Access token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          autoFocus
        />
        {error && <p className="jd-error">{error}</p>}
        <button className="btn btn-accent" type="submit" disabled={!token.trim()}>
          Unlock
        </button>
      </form>
    </div>
  );
}
