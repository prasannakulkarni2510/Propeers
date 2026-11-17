import CvDeck from "../components/CvDeck.jsx";

// Your CV is what every message is written from, so it gets its own place.
export default function MyCv() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">My CV</h1>
          <p className="page-sub">
            Keep a CV for each kind of role. Every email and LinkedIn DM is written from the one in use,
            using only your real experience.
          </p>
        </div>
      </div>
      <CvDeck />
    </div>
  );
}
