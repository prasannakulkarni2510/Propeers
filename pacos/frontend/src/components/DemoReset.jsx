import { useEffect, useState } from "react";
import { api } from "../services/api";

// Sidebar control on a public demo: put the saved demo back (people, stages,
// drafts; chats cleared; dates moved up to today), or save what's on screen
// as the demo. Hidden on a normal install, where the server turns it off.
export default function DemoReset() {
  const [demo, setDemo] = useState(null); // { enabled, saved_on }
  const [ask, setAsk] = useState(""); // "" | "reset" | "save"
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.demo().then(setDemo).catch(() => {});
  }, []);

  if (!demo?.enabled) return null;

  const run = async () => {
    setBusy(true);
    setMsg("");
    try {
      if (ask === "reset") {
        await api.resetDemo();
        window.location.assign("/"); // fresh start: every page reloads its data
        return;
      }
      const r = await api.saveDemo();
      setDemo({ enabled: true, saved_on: r.saved_on });
      setMsg(`Saved ${r.people} people as the demo.`);
      setAsk("");
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (ask) {
    return (
      <div className="demo-ask" role="group" aria-label={ask === "reset" ? "Reset the demo" : "Save the demo"}>
        <p>
          {ask === "reset"
            ? "Put back the saved demo? Chats and changes since then are cleared; dates move up to today."
            : "Save everyone, their stages and drafts as the demo?"}
        </p>
        <div className="demo-ask-row">
          <button className="btn btn-accent btn-sm" disabled={busy} onClick={run}>
            {busy ? "Working…" : ask === "reset" ? "Reset" : "Save"}
          </button>
          <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => setAsk("")}>Cancel</button>
        </div>
        {msg && <p className="demo-msg">{msg}</p>}
      </div>
    );
  }

  return (
    <>
      {demo.saved_on && (
        <button className="nav-quiet" onClick={() => setAsk("reset")} title={`Saved ${demo.saved_on}`}>
          Reset demo
        </button>
      )}
      <button className="nav-quiet" onClick={() => setAsk("save")}>
        {demo.saved_on ? "Save as demo" : "Save this as the demo"}
      </button>
      {msg && <p className="demo-msg">{msg}</p>}
    </>
  );
}
