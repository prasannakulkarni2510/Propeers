import { useEffect, useRef, useState } from "react";

// Full-screen intro shown on every visit (every page load, not every route
// change: App mounts once). Closes on Skip, Escape, or when the video ends.
const SRC = "/pacos-intro.mp4";

export default function IntroVideo() {
  const [open, setOpen] = useState(true);
  const [muted, setMuted] = useState(false);
  const videoRef = useRef(null);
  const skipRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    skipRef.current?.focus();
    // Browsers block autoplay with sound until the visitor interacts with the
    // page, so try with sound first and fall back to muted.
    const v = videoRef.current;
    v?.play().catch(() => {
      if (!v) return;
      v.muted = true;
      setMuted(true);
      v.play().catch(() => {});
    });
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;

  const toggleMute = () => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
  };

  return (
    <div className="intro" role="dialog" aria-modal="true" aria-label="PACOS intro video">
      <video
        ref={videoRef}
        className="intro-video"
        src={SRC}
        playsInline
        preload="auto"
        onEnded={() => setOpen(false)}
        onError={() => setOpen(false)}
      />
      <div className="intro-controls">
        <button className="intro-btn" onClick={toggleMute}>
          {muted ? "🔇 Unmute" : "🔊 Mute"}
        </button>
        <button ref={skipRef} className="intro-btn intro-skip" onClick={() => setOpen(false)}>
          Skip intro →
        </button>
      </div>
    </div>
  );
}
