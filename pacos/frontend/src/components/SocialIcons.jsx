import Icon from "./Icon.jsx";
import { SOCIAL } from "../lib/social";

// LinkedIn, GitHub and email as a row of small icon links.
export default function SocialIcons({ className = "" }) {
  return (
    <nav className={`social-icons ${className}`} aria-label="Prasanna Kulkarni elsewhere">
      {SOCIAL.map((s) => (
        <a
          key={s.label}
          className="icon-btn social-icon"
          href={s.href}
          target={s.href.startsWith("mailto:") ? undefined : "_blank"}
          rel="noopener noreferrer"
          aria-label={s.label}
          title={s.label}
        >
          <Icon name={s.icon} size={18} />
        </a>
      ))}
    </nav>
  );
}
