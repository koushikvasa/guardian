"use client";
import { CaseState } from "@/lib/guardian";
import { mainCall } from "./Desk";

/** The hero object for the current beat, drawn live from case state: the jar (links), the two keys (money), the callback ring (family claims). */
export function Hero({ c }: { c: CaseState }) {
  if (c.money) return <Keys c={c} />;
  if (c.calls.verify || (c.text && /it'?s me|soy |నేను /i.test(c.text) && !c.detonation)) return <Ring c={c} />;
  return <Jar c={c} />;
}

const T = "transform .8s cubic-bezier(.2,.8,.2,1), opacity .6s";

function Jar({ c }: { c: CaseState }) {
  const d = c.detonation;
  const sealed = !!d;
  const gone = d?.sandbox_destroyed_s != null;
  return (
    <svg viewBox="0 0 320 240" style={{ width: "100%", height: "100%", maxHeight: 420 }} role="img" aria-label="The link, opened inside a sealed sandbox">
      <path d="M100 70 h120 v120 a14 14 0 0 1 -14 14 h-92 a14 14 0 0 1 -14 -14 z" fill="rgba(255,255,255,.65)" stroke={gone ? "#14705A" : "#C3CBE0"} strokeWidth="3" style={{ transition: "stroke .6s" }} />
      <rect x="112" y="78" width="6" height="110" rx="3" fill="rgba(255,255,255,.9)" />
      <g style={{ transition: T, transformOrigin: "160px 140px", transform: gone ? "scale(0.06) rotate(30deg)" : "none", opacity: gone ? 0 : 1 }}>
        <g style={{ transition: T, transformOrigin: "160px 140px", transform: sealed ? "rotate(-2deg)" : "rotate(4deg) translateY(-6px)" }}>
          <rect x="128" y="96" width="64" height="84" rx="4" fill="#fff" stroke="#D5DAE6" />
          <rect x="128" y="96" width="64" height="12" rx="4" fill="#23408E" />
          <rect x="136" y="118" width="48" height="8" rx="2" fill="#DADFE8" /><rect x="136" y="132" width="48" height="8" rx="2" fill="#DADFE8" /><rect x="136" y="146" width="48" height="8" rx="2" fill="#DADFE8" />
          <rect x="136" y="162" width="48" height="10" rx="2" fill="#23408E" />
        </g>
      </g>
      <rect x="92" y={sealed ? 52 : 14} width="136" height="18" rx="6" fill="#161B33" style={{ transition: T }} />
      {gone && <g transform="translate(236 62)"><circle r="13" fill="#14705A" /><path d="M-5.5 0 L-1.5 4 L6 -4.5" stroke="#fff" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" /></g>}
      <text x="160" y="222" textAnchor="middle" fontSize="13" fill={gone ? "#14705A" : "#4A5170"} fontFamily="Figtree, sans-serif" fontWeight={gone ? 700 : 500}>
        {gone ? `Sandbox destroyed in ${d?.sandbox_destroyed_s} s · nothing touched her phone` : sealed ? "Sealed in a Daytona sandbox" : c.text && /https?:|\.[a-z]{2,}\//.test(c.text) ? "Opening the link away from her phone…" : "No link in this one"}
      </text>
    </svg>
  );
}

function Keys({ c }: { c: CaseState }) {
  const st = c.money?.state;
  const key = (x: number, turned: boolean, color: string) => (
    <g transform={`translate(${x} 110)`}>
      <circle r="46" fill="#0D1124" />
      <g style={{ transition: T, transformOrigin: "0 0", transform: turned ? "rotate(-90deg)" : "none" }}>
        <rect x="-34" y="-7" width="68" height="14" rx="7" fill={color} />
        <circle cx="-18" cy="0" r="4.5" fill="#0D1124" />
        <rect x="-34" y="-7" width="68" height="4" rx="2" fill="#E7C77A" opacity=".8" />
      </g>
    </g>
  );
  return (
    <svg viewBox="0 0 320 240" style={{ width: "100%", height: "100%", maxHeight: 420 }} role="img" aria-label="Two keys: hers is turned; Daniel's decides">
      <rect x="20" y="30" width="280" height="170" rx="24" fill="#161B33" />
      {key(100, true, "#B8862B")}
      {st === "locked" && <circle cx="220" cy="110" r="46" fill="none" stroke="#E7C77A" strokeWidth="3" strokeDasharray="8 9" style={{ transformOrigin: "220px 110px", animation: "spin 12s linear infinite" }} />}
      {st === "declined" ? (
        <g transform="translate(220 110)"><circle r="46" fill="#0D1124" /><circle r="38" fill="none" stroke="#F0645C" strokeWidth="5" /><path d="M-18 -18 L18 18 M18 -18 L-18 18" stroke="#F0645C" strokeWidth="8" strokeLinecap="round" /></g>
      ) : key(220, st === "approved", st === "approved" ? "#B8862B" : "#2C3352")}
      <text x="100" y="180" textAnchor="middle" fontSize="12" fill="#B9C0DA" fontFamily="Figtree, sans-serif">{c.protected}&rsquo;s key</text>
      <text x="220" y="180" textAnchor="middle" fontSize="12" fill={st === "declined" ? "#F7A9A4" : "#B9C0DA"} fontFamily="Figtree, sans-serif">Daniel&rsquo;s key</text>
      <text x="160" y="226" textAnchor="middle" fontSize="13" fill={st === "declined" ? "#D7322A" : st === "approved" ? "#14705A" : "#6B4A10"} fontFamily="Figtree, sans-serif" fontWeight={700}>
        {st === "locked" ? `$${c.money?.amount.toLocaleString()} locked · Guardian cannot approve · no timeout` : st === "declined" ? "Stopped by Daniel. Nothing moved." : "Both keys turned by family. Guardian turned neither."}
      </text>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </svg>
  );
}

function Ring({ c }: { c: CaseState }) {
  const mc = mainCall(c);
  const calling = !!c.calls.verify;
  const live = mc?.key === "verify" && mc.live;
  const denied = c.verify === "denied";
  const confirmed = c.verify === "confirmed";
  return (
    <svg viewBox="0 0 320 240" style={{ width: "100%", height: "100%", maxHeight: 420 }} role="img" aria-label="Guardian calls the real relative on the saved number">
      <line x1="64" y1="140" x2="160" y2="110" stroke="#D7322A" strokeWidth="3" strokeDasharray="8 7" style={{ transition: T, opacity: denied ? 0.25 : 1 }} />
      <line x1="160" y1="110" x2="256" y2="80" stroke="#2E46E5" strokeWidth="4" strokeDasharray="110" strokeDashoffset={calling ? 0 : 110} style={{ transition: "stroke-dashoffset 1.2s ease-out" }} />
      <g transform="translate(64 140)" style={{ transition: T, opacity: denied ? 0.35 : 1, transform: denied ? "translate(64px, 170px)" : undefined }}>
        <circle r="30" fill="#F7E9E8" stroke="#D7322A" strokeWidth="3" strokeDasharray="7 6" />
        <text y="5" textAnchor="middle" fontSize="12" fill="#8C1D18" fontFamily="Figtree, sans-serif" fontWeight={700}>{c.sender ? c.sender.replace("a number ending ", "…") : "unknown"}</text>
      </g>
      <g transform="translate(160 110)"><circle r="34" fill="#2E46E5" /><text y="9" textAnchor="middle" fontSize="28" fill="#fff" fontFamily="'Young Serif', serif">{(c.protected || "A")[0]}</text></g>
      <g transform="translate(256 80)">
        <circle r="30" fill="#fff" stroke={denied || confirmed ? "#14705A" : "#2E46E5"} strokeWidth="4" />
        <text y="9" textAnchor="middle" fontSize="26" fill="#161B33" fontFamily="'Young Serif', serif">D</text>
        {live && <circle r="38" fill="none" stroke="#9EB0FF" strokeWidth="3" style={{ transformOrigin: "0 0", animation: "pulse 1.2s ease-out infinite" }} />}
        {(denied || confirmed) && <g transform="translate(22 -22)"><circle r="12" fill="#14705A" /><path d="M-5 0 L-1.5 3.5 L5 -4" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /></g>}
      </g>
      <text x="64" y="196" textAnchor="middle" fontSize="12" fill="#4A5170" fontFamily="Figtree, sans-serif">the caller</text>
      <text x="262" y="124" textAnchor="middle" fontSize="12" fill="#4A5170" fontFamily="Figtree, sans-serif">the real Daniel</text><text x="262" y="138" textAnchor="middle" fontSize="11" fill="#4A5170" fontFamily="Figtree, sans-serif">saved number</text>
      <text x="160" y="226" textAnchor="middle" fontSize="13" fill={denied ? "#14705A" : "#4A5170"} fontFamily="Figtree, sans-serif" fontWeight={700}>
        {denied ? "Daniel is at work. It wasn't him." : confirmed ? "Daniel says it was him. She still waits for his direct call." : live ? "Calling Daniel on his saved number…" : calling ? "Daniel didn't pick up yet. Nothing is sent." : "Someone says they're Daniel. Guardian asks the real one."}
      </text>
      <style>{`@keyframes pulse { 0% { transform: scale(.8); opacity: 1 } 100% { transform: scale(1.5); opacity: 0 } }`}</style>
    </svg>
  );
}
