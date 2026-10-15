"use client";
import { useEffect, useId, useRef } from "react";

export type Mood = "idle" | "reading" | "suspicious" | "scam" | "calling" | "safe";
export type Look = { x: number; y: number } | null;

const COLOR: Record<Mood, string> = { idle: "#2E46E5", reading: "#2E46E5", suspicious: "#2E46E5", scam: "#D7322A", calling: "#2E46E5", safe: "#14705A" };
const PUPIL: Record<Mood, number> = { idle: 2.3, reading: 2.1, suspicious: 1.7, scam: 2.7, calling: 2.2, safe: 2.3 };

/** The living Guardian mark. Eyes follow `look` (or the pointer when null), blink on their own, and the slot
 *  tilts in 3D toward wherever it looks. Mood changes colour, pupil size and brows. Pure SVG + CSS: no WebGL. */
export function Mark({ size = 92, mood = "idle", look = null, tilt = true, title }: { size?: number; mood?: Mood; look?: Look; tilt?: boolean; title?: string }) {
  const id = useId().replace(/:/g, "");
  const root = useRef<HTMLDivElement>(null);
  const state = useRef({ x: 0, y: 0, tx: 0, ty: 0, blink: 0, next: 2 + Math.random() * 3, pupil: 2.3, scan: 0, lastMood: mood });
  const moodRef = useRef(mood);
  const lookRef = useRef(look);
  moodRef.current = mood;
  lookRef.current = look;

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      state.current.tx = Math.max(-1, Math.min(1, (e.clientX - r.left - r.width / 2) / 360));
      state.current.ty = Math.max(-1, Math.min(1, (e.clientY - r.top - r.height / 2) / 300));
    };
    window.addEventListener("pointermove", onMove);
    const pupils = el.querySelectorAll<SVGCircleElement>(".p");
    const glints = el.querySelectorAll<SVGCircleElement>(".h");
    const lids = el.querySelectorAll<SVGRectElement>(".lid");
    const brows = el.querySelectorAll<SVGRectElement>(".brow");
    const slot = el.querySelector<SVGRectElement>(".slot");
    let raf = 0, last = performance.now();
    const frame = (now: number) => {
      const s = state.current, m = moodRef.current, lk = lookRef.current;
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      if (m !== s.lastMood) { s.lastMood = m; if (m === "safe") { s.blink = 1; setTimeout(() => { s.blink = 1; }, 420); } }
      let tx = lk ? lk.x : s.tx, ty = lk ? lk.y : s.ty;
      if (m === "reading" && !lk) { s.scan += dt; tx = Math.sin(s.scan * 2.2) * 0.9; ty = 0.25; }
      const k = reduce ? 1 : 0.12;
      s.x += (tx - s.x) * k; s.y += (ty - s.y) * k;
      s.pupil += (PUPIL[m] - s.pupil) * 0.1;
      s.next -= dt; if (s.next <= 0 && !reduce) { s.blink = 1; s.next = 2.5 + Math.random() * 3.5; }
      let lid = 0; if (s.blink > 0) { s.blink = Math.max(0, s.blink - dt * 6); lid = Math.sin(s.blink * Math.PI); }
      const brow = m === "suspicious" || m === "scam" ? 1 : 0;
      const dx = s.x * 2.2, dy = s.y * 1.6, c = COLOR[m];
      pupils.forEach((p, i) => { p.setAttribute("cx", String((i ? 30.25 : 18.75) + dx)); p.setAttribute("cy", String(21 + dy)); p.setAttribute("r", String(s.pupil)); p.setAttribute("fill", c); });
      glints.forEach((g, i) => { g.setAttribute("cx", String((i ? 31 : 19.5) + dx * 0.9)); g.setAttribute("cy", String(20.2 + dy * 0.9)); });
      lids.forEach((l) => { l.setAttribute("y", String(4 + lid * 9.6 + brow * 2.2)); l.setAttribute("fill", c); });
      brows.forEach((b, i) => { b.setAttribute("opacity", String(brow)); b.setAttribute("fill", c); b.setAttribute("transform", brow ? (i ? "rotate(-8 30 11.2)" : "rotate(8 19 11.2)") : ""); });
      slot?.setAttribute("fill", c);
      if (tilt && !reduce) el.style.transform = `rotateY(${s.x * 14}deg) rotateX(${-s.y * 10}deg)`;
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("pointermove", onMove); };
  }, [tilt]);

  return (
    <div ref={root} style={{ width: size, flexShrink: 0, transformStyle: "preserve-3d", transition: "transform .2s", filter: "drop-shadow(0 8px 12px rgba(22,27,51,.18))" }} aria-hidden={title ? undefined : true} role={title ? "img" : undefined} aria-label={title}>
      <svg viewBox="6 9 36 22" style={{ width: "100%", height: "auto", display: "block", overflow: "visible" }}>
        <defs>
          <linearGradient id={`${id}s`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff" stopOpacity=".28" /><stop offset=".5" stopColor="#fff" stopOpacity="0" /></linearGradient>
          <clipPath id={`${id}L`}><path d="M15.59 16.5 H21.91 A5.5 5.5 0 0 1 21.91 25.5 H15.59 A5.5 5.5 0 0 1 15.59 16.5 Z" /></clipPath>
          <clipPath id={`${id}R`}><path d="M27.09 16.5 H33.41 A5.5 5.5 0 0 1 33.41 25.5 H27.09 A5.5 5.5 0 0 1 27.09 16.5 Z" /></clipPath>
        </defs>
        <rect className="slot" x="7.5" y="13" width="34" height="16" rx="8" fill="#2E46E5" />
        <rect x="7.5" y="13" width="34" height="16" rx="8" fill={`url(#${id}s)`} />
        <path d="M15.59 16.5 H21.91 A5.5 5.5 0 0 1 21.91 25.5 H15.59 A5.5 5.5 0 0 1 15.59 16.5 Z" fill="var(--eye)" />
        <path d="M27.09 16.5 H33.41 A5.5 5.5 0 0 1 33.41 25.5 H27.09 A5.5 5.5 0 0 1 27.09 16.5 Z" fill="var(--eye)" />
        <g clipPath={`url(#${id}L)`}><circle className="p" cx="18.75" cy="21" r="2.3" fill="#2E46E5" /><circle className="h" cx="19.5" cy="20.2" r=".6" fill="#fff" /></g>
        <g clipPath={`url(#${id}R)`}><circle className="p" cx="30.25" cy="21" r="2.3" fill="#2E46E5" /><circle className="h" cx="31" cy="20.2" r=".6" fill="#fff" /></g>
        <g clipPath={`url(#${id}L)`}><rect className="lid" x="15" y="4" width="8" height="9.6" fill="#2E46E5" /></g>
        <g clipPath={`url(#${id}R)`}><rect className="lid" x="26.5" y="4" width="8" height="9.6" fill="#2E46E5" /></g>
        <rect className="brow" x="14.5" y="10.6" width="9" height="1.2" rx=".6" fill="#2E46E5" opacity="0" />
        <rect className="brow" x="25.5" y="10.6" width="9" height="1.2" rx=".6" fill="#2E46E5" opacity="0" />
      </svg>
    </div>
  );
}


/** The brand lockup: a larger mark, vertically centred on the wordmark. */
export function Brand({ size = 56, mood = "idle", href }: { size?: number; mood?: Mood; href?: string }) {
  const inner = (
    <span style={{ display: "inline-flex", alignItems: "center", gap: Math.round(size * 0.22), fontWeight: 700, fontSize: Math.round(size * 0.46), lineHeight: 1, color: "inherit" }}>
      <Mark size={size} mood={mood} tilt={false} />
      <span style={{ transform: "translateY(1px)" }}>Guardian</span>
    </span>
  );
  return href ? <a href={href} style={{ textDecoration: "none", color: "inherit" }}>{inner}</a> : inner;
}
