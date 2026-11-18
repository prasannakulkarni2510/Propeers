import { useState } from "react";
import Icon from "./Icon.jsx";
import { SOCIAL } from "../lib/social";

// The author, for the About page's right-hand column: photo with an animated
// "open to work" ring and badge, name, role, and where to reach him.
export default function AuthorCard() {
  const [photoOk, setPhotoOk] = useState(true);
  return (
    <div className="panel author-card">
      <div className="author-photo">
        <span className="author-ring" aria-hidden="true" />
        {photoOk ? (
          <img src="/author-photo.jpg" alt="Prasanna Kulkarni" onError={() => setPhotoOk(false)} />
        ) : (
          <div className="about-avatar-fallback">PK</div>
        )}
        <span className="open-badge">
          <span className="open-dot" aria-hidden="true" />
          Open to work
        </span>
      </div>
      <h2 className="author-name">Prasanna Kulkarni</h2>
      <p className="author-role">AI Engineer, builder of PACOS</p>
      <p className="author-seeking">Looking for data science and AI roles in India.</p>
      <ul className="author-links">
        {SOCIAL.map((s) => (
          <li key={s.label}>
            <a
              className="author-link"
              href={s.href}
              target={s.href.startsWith("mailto:") ? undefined : "_blank"}
              rel="noopener noreferrer"
            >
              <Icon name={s.icon} size={16} />
              <span>{s.icon === "mail" ? s.text : s.label}</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
