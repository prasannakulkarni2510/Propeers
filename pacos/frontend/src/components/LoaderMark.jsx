import { useEffect, useRef } from "react";

// The PACOS wordmark with the "O" drawn as a spinning ring: four arcs that
// grow and then shrink one after another while the whole ring turns. It is a
// plain-JS port of the LottieFiles loader at
// lottie.host/764d6185-0aea-494c-82c7-e7c6bd114d85 (same timings, in frames at
// 60fps), redrawn in the brand colour so no animation library is needed.

const FPS = 60;
const CYCLE = 141; // frames per loop
const SHRINK_END = 119; // every arc has collapsed by this frame
const DEG_PER_FRAME = 6; // 1080° every 180 frames
// [frame the arc starts growing, frame it starts shrinking]
const ARCS = [[0, 60], [20, 69.9], [41, 80.3], [54, 86.8]];
// Each loop ends with a short stub at 67–70% of the ring; turning the next
// loop on by that much makes the stub carry on instead of jumping back.
const LOOP_TURN = 0.67 * 360;

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const part = (f, a, b) => ease(Math.min(1, Math.max(0, (f - a) / (b - a))));

// Start and end of one arc, as a percent of the ring, at frame f of a loop.
function trim(f, [grow, shrink]) {
  if (f < shrink) return [0, 3 + 67 * part(f, grow, shrink)];
  return [67 * part(f, shrink, SHRINK_END), 70];
}

const R = 42;
const STROKE = 15.5; // matches the weight of Geist Bold at this size

export default function LoaderMark() {
  const turnRef = useRef(null);
  const arcRefs = useRef([]);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
    let raf = 0;
    const t0 = performance.now();
    const draw = (now) => {
      const frames = ((now - t0) / 1000) * FPS;
      const loop = Math.floor(frames / CYCLE);
      const f = frames - loop * CYCLE;
      const deg = (frames * DEG_PER_FRAME + loop * LOOP_TURN) % 360;
      turnRef.current?.setAttribute("transform", `rotate(${deg - 90} 50 50)`);
      ARCS.forEach((arc, i) => {
        const el = arcRefs.current[i];
        if (!el) return;
        const [s, e] = trim(f, arc);
        el.setAttribute("stroke-dasharray", `${e - s} ${100 - (e - s)}`);
        el.setAttribute("stroke-dashoffset", String(-s));
      });
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <span className="loader-mark" role="img" aria-label="PACOS">
      <span aria-hidden="true">PAC</span>
      <svg className="loader-o" viewBox="0 0 100 100" aria-hidden="true">
        <circle className="loader-o-track" cx="50" cy="50" r={R} strokeWidth={STROKE} />
        <g ref={turnRef} transform="rotate(-90 50 50)">
          {ARCS.map((_, i) => (
            <circle
              key={i}
              ref={(el) => { arcRefs.current[i] = el; }}
              className="loader-o-arc"
              cx="50"
              cy="50"
              r={R}
              strokeWidth={STROKE}
              pathLength="100"
              strokeDasharray="3 97"
            />
          ))}
        </g>
      </svg>
      <span aria-hidden="true" className="brand-accent">S</span>
    </span>
  );
}
