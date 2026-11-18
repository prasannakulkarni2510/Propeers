import { useEffect, useState } from "react";
import { api, authToken } from "../services/api";
import LoaderMark from "./LoaderMark.jsx";
import ContactForm from "./ContactForm.jsx";

// The loading screen stays up for at least this long so it reads as a
// deliberate splash rather than a flicker, then fades out.
const SPLASH_MIN_MS = 1000;
const SPLASH_FADE_MS = 280;

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
  const [splash, setSplash] = useState("on"); // on | leaving | off

  useEffect(() => {
    if (state !== "locked") return;
    api.loginTrial()
      .then((t) => t.email && setTrial(t))
      .catch(() => {});
  }, [state]);

  const probe = async () => {
    const started = performance.now();
    let next = "ok";
    try {
      await api.stats();
    } catch (e) {
      if (e.status === 401) authToken.set(""); // stale session: drop it
      if (e.status === 401) next = "locked";
    }
    const wait = SPLASH_MIN_MS - (performance.now() - started);
    if (wait > 0) await new Promise((done) => setTimeout(done, wait));
    setState(next);
    setSplash("leaving");
    setTimeout(() => setSplash("off"), SPLASH_FADE_MS);
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

  const splashScreen = splash !== "off" && (
    <div className={`splash ${splash === "leaving" ? "is-leaving" : ""}`} role="status" aria-live="polite">
      <LoaderMark />
      <p className="muted splash-note">Connecting…</p>
    </div>
  );

  if (state === "checking") return splashScreen;
  if (state === "ok") return <>{children}{splashScreen}</>;
  return (
    <>
    {splashScreen}
    <div className="authgate">
      <div className="authgate-stack">
        <form className="panel authgate-card" onSubmit={login}>
          <div className="brand">
            PAC<span className="brand-accent">OS</span>
          </div>
          <h1>Log in</h1>
          <input
            className="input"
            type="email"
            aria-label="Email"
            placeholder="Email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
          <input
            className="input"
            type="password"
            aria-label="Password"
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
              <p>Just looking? Use the trial login:</p>
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
        <ContactForm page="login" collapsed />
      </div>
    </div>
    </>
  );
}
