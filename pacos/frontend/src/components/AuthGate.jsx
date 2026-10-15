import { useEffect, useState } from "react";
import { api, authToken } from "../services/api";

// Gate for cloud deployments: when the backend has PACOS_LOGIN_EMAIL and
// PACOS_LOGIN_PASSWORD set, every /api call needs a session token. We probe
// once with /api/stats — a 401 shows the login form; any other outcome
// (including backend-down) lets the app render normally so local/exe usage is
// untouched.
export default function AuthGate({ children }) {
  const [state, setState] = useState("checking"); // checking | locked | ok
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [trial, setTrial] = useState(null); // { email, password } when public

  useEffect(() => {
    if (state !== "locked") return;
    api.loginTrial()
      .then((t) => t.email && setTrial(t))
      .catch(() => {});
  }, [state]);

  const probe = async () => {
    try {
      await api.stats();
      setState("ok");
    } catch (e) {
      if (e.status === 401) authToken.set(""); // stale session: drop it
      setState(e.status === 401 ? "locked" : "ok");
    }
  };

  useEffect(() => {
    probe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { token } = await api.login(email.trim(), password);
      authToken.set(token);
      setPassword("");
      setState("ok");
    } catch (err) {
      setError(err.status === 401 ? "Wrong email or password." : err.message);
    } finally {
      setBusy(false);
    }
  };

  if (state === "checking") return <div className="authgate"><p className="muted">Connecting…</p></div>;
  if (state === "ok") return children;
  return (
    <div className="authgate">
      <form className="panel authgate-card" onSubmit={login}>
        <div className="brand">
          PAC<span className="brand-accent">OS</span>
        </div>
        <p className="muted">Log in to continue.</p>
        <input
          className="input"
          type="email"
          placeholder="Email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoFocus
        />
        <input
          className="input"
          type="password"
          placeholder="Password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="jd-error" role="alert">{error}</p>}
        <button
          className="btn btn-accent"
          type="submit"
          disabled={busy || !email.trim() || !password}
        >
          {busy ? "Logging in…" : "Log in"}
        </button>
        {trial && (
          <div className="authgate-trial">
            <p>For trial use, you may use these credentials:</p>
            <dl>
              <dt>Email</dt><dd>{trial.email}</dd>
              <dt>Password</dt><dd>{trial.password}</dd>
            </dl>
            <button
              type="button"
              className="authgate-trial-fill"
              onClick={() => { setEmail(trial.email); setPassword(trial.password); setError(""); }}
            >
              Fill them in
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
