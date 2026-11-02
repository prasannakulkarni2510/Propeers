import { useLeads } from "../hooks/useLeads";
import Dashboard from "../components/Dashboard.jsx";
import CvEditor from "../components/CvEditor.jsx";

export default function Home() {
  const { error } = useLeads();
  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">Generate outreach for your leads and watch the agents run.</p>
      {error && <div className="banner">Backend error: {error}</div>}
      <CvEditor />
      <Dashboard />
    </div>
  );
}
