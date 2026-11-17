// One small stroke icon set (24px grid, currentColor) in place of emoji and
// typed glyphs, so icons follow the text colour and size.
const PATHS = {
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  "arrow-left": <path d="M19 12H5M11 6l-6 6 6 6" />,
  "arrow-down": <path d="M12 5v14M6 13l6 6 6-6" />,
  calendar: (
    <>
      <rect x="4" y="5.5" width="16" height="14" rx="2" />
      <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
    </>
  ),
  image: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <circle cx="9" cy="10" r="1.6" />
      <path d="M20 16l-5-5-8 8" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  more: (
    <>
      <circle cx="6" cy="12" r="1.2" fill="currentColor" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" />
      <circle cx="18" cy="12" r="1.2" fill="currentColor" />
    </>
  ),
  star: <path d="M12 4l2.5 5.1 5.6.8-4.05 3.95.95 5.6L12 16.8l-5 2.65.95-5.6L3.9 9.9l5.6-.8z" />,
  "star-fill": <path fill="currentColor" d="M12 4l2.5 5.1 5.6.8-4.05 3.95.95 5.6L12 16.8l-5 2.65.95-5.6L3.9 9.9l5.6-.8z" />,
  pencil: <path d="M4 20l1-4.5L16.5 4a2 2 0 013 3L8 18.5 4 20zM14.5 6l3.5 3.5" />,
  trash: <path d="M5 7h14M10 7V4.5h4V7M7 7l1 12.5h8L17 7M10.5 11v5M13.5 11v5" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  message: <path d="M5 5.5h14a1.5 1.5 0 011.5 1.5v9a1.5 1.5 0 01-1.5 1.5h-7.5L7 21v-3.5H5A1.5 1.5 0 013.5 16V7A1.5 1.5 0 015 5.5zM8 10h8M8 13.5h5" />,
  mail: (
    <>
      <rect x="3.5" y="5.5" width="17" height="13" rx="2" />
      <path d="M4 7.5l8 6 8-6" />
    </>
  ),
  layers: <path d="M12 4l8.5 4.5L12 13 3.5 8.5 12 4zM3.5 12.5L12 17l8.5-4.5M3.5 16.5L12 21l8.5-4.5" />,
  download: <path d="M12 4v11M7 10.5l5 5 5-5M5 19.5h14" />,
  play: <path d="M8 5.5v13l10.5-6.5z" />,
  external: <path d="M8 16L16.5 7.5M9.5 7.5h7v7" />,
  linkedin: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="2.5" />
      <path d="M8.5 10.5V16M8.5 7.8v.2M12 16v-5.5M12 13a2 2 0 014 0v3" />
    </>
  ),
  "sound-on": <path d="M4 10v4h3.5L12 18V6L7.5 10H4zM15.5 9a4 4 0 010 6M18 6.5a7.5 7.5 0 010 11" />,
  "sound-off": <path d="M4 10v4h3.5L12 18V6L7.5 10H4zM16 9.5l5 5M21 9.5l-5 5" />,
};

export default function Icon({ name, size = 16, className = "" }) {
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
