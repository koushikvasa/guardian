"use client";
import { useEffect, useRef } from "react";
import { CaseState } from "@/lib/guardian";
import { mainCall } from "./Desk";

/** The hero object for the current beat, drawn live from case state and animated on each state change:
 *  the jar (links), the two keys (money), the callback ring (family claims). Keyframes live in globals.css. */
export function Hero({ c }: { c: CaseState }) {
  if (c.money) return <Keys c={c} />;
  if (c.calls.verify || (c.text && /it'?s me|soy |నేను /i.test(c.text) && !c.detonation)) return <Ring c={c} />;
  return <Jar c={c} />;
}

function Jar({ c }: { c: CaseState }) {
  const d = c.detonation;
  const sealed = !!d;
  const gone = d?.sandbox_destroyed_s != null;
  const wasSealed = useRef(false);
  useEffect(() => { if (sealed) wasSealed.current = true; }, [sealed]);
  // if the seal and the destruction arrive together, the shatter waits for the lid; otherwise it plays at once
  const shatterDelay = gone && !wasSealed.current ? "1.6s" : "0.2s";
  const shards = [[-60, -50], [70, -40], [-50, 40], [60, 50], [0, -70], [0, 70]];
  return (
    <svg viewBox="0 0 320 240" className={`hero jar${sealed ? " sealed" : ""}${gone ? " gone" : ""}`} style={{ width: "100%", height: "100%", maxHeight: 420, ["--shatter" as string]: shatterDelay }} role="img" aria-label="The link, opened inside a sealed sandbox">
      <g className="glass">
        <path d="M100 70 h120 v120 a14 14 0 0 1 -14 14 h-92 a14 14 0 0 1 -14 -14 z" fill="var(--page)" fillOpacity=".75" stroke={gone ? "var(--ok)" : "#C3CBE0"} strokeWidth="3" style={{ transition: "stroke .6s" }} />
        <rect x="112" y="78" width="6" height="110" rx="3" fill="#fff" fillOpacity=".9" />
      </g>
      <g className="pageg">
        <g className="float">
          <rect x="128" y="96" width="64" height="84" rx="4" fill="var(--page)" stroke="var(--line)" />
          <rect x="128" y="96" width="64" height="12" rx="4" fill="#23408E" />
          <rect x="136" y="118" width="48" height="8" rx="2" fill="#DADFE8" /><rect x="136" y="132" width="48" height="8" rx="2" fill="#DADFE8" /><rect x="136" y="146" width="48" height="8" rx="2" fill="#DADFE8" />
          <rect x="136" y="162" width="48" height="10" rx="2" fill="#23408E" />
        </g>
      </g>
      {shards.map(([dx, dy], i) => <rect key={i} className="shard" x={150 + (i % 3) * 8} y={118 + (i % 2) * 14} width={10 - i} height={10 - i} fill={["#C9D3F5", "#9EB0FF", "#DCE2FF"][i % 3]} style={{ ["--dx" as string]: `${dx}px`, ["--dy" as string]: `${dy}px` }} />)}
      <rect className="lid" x="92" y="52" width="136" height="18" rx="6" fill="var(--dark)" />
      <g transform="translate(236 62)"><g className="okmark"><circle r="13" fill="var(--ok)" /><path d="M-5.5 0 L-1.5 4 L6 -4.5" stroke="#fff" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" /></g></g>
      <text className="label" x="160" y="222" textAnchor="middle" fontSize="12" fill={gone ? "var(--ok)" : "var(--muted)"} fontFamily="Figtree, sans-serif" fontWeight={gone ? 700 : 500}>
        {gone ? `Sandbox destroyed in ${d?.sandbox_destroyed_s} s · nothing touched her phone` : sealed ? "Sealed in a Daytona sandbox" : c.text && /https?:|\.[a-z]{2,}\//.test(c.text) ? "Opening the link away from her phone…" : "No link in this one"}
      </text>
    </svg>
  );
}

function Keys({ c }: { c: CaseState }) {
  const st = c.money?.state;
  const key = (turned: boolean, color: string, cls?: string) => (
    <g className={cls}>
      <g style={{ transform: turned ? "rotate(-90deg)" : undefined }}>
        <rect x="-34" y="-7" width="68" height="14" rx="7" fill={color} />
        <circle cx="-18" cy="0" r="4.5" fill="var(--dark2)" />
        <rect x="-34" y="-7" width="68" height="4" rx="2" fill="#E7C77A" opacity=".8" />
      </g>
    </g>
  );
  return (
    <svg viewBox="0 0 320 240" className={`hero vault ${st || "none"}`} style={{ width: "100%", height: "100%", maxHeight: 420 }} role="img" aria-label="Two keys: hers is turned; Daniel's decides">
      <g className="door">
        <rect x="20" y="30" width="280" height="170" rx="24" fill="var(--dark)" />
        <circle className="lamp" cx="160" cy="50" r="6" fill={st === "approved" ? "#3DBF9A" : st === "declined" ? "#F0645C" : "#E7C77A"} />
        <g transform="translate(100 110)"><circle r="46" fill="var(--dark2)" />{key(true, "#B8862B")}</g>
        <g transform="translate(220 110)">
          <circle r="46" fill="var(--dark2)" />
          <circle className="waitring" r="46" fill="none" stroke="#E7C77A" strokeWidth="3" strokeDasharray="8 9" />
          {st === "declined" ? (
            <g className="refuse"><circle className="xring" r="38" fill="none" stroke="#F0645C" strokeWidth="5" /><path className="xline x1" d="M-18 -18 L18 18" stroke="#F0645C" strokeWidth="8" strokeLinecap="round" /><path className="xline x2" d="M18 -18 L-18 18" stroke="#F0645C" strokeWidth="8" strokeLinecap="round" /></g>
          ) : key(false, st === "approved" ? "#B8862B" : "#2C3352", "keyD")}
        </g>
        <text x="100" y="180" textAnchor="middle" fontSize="12" fill="#B9C0DA" fontFamily="Figtree, sans-serif">{c.protected}&rsquo;s key</text>
        <text x="220" y="180" textAnchor="middle" fontSize="12" fill={st === "declined" ? "#F7A9A4" : "#B9C0DA"} fontFamily="Figtree, sans-serif">Daniel&rsquo;s key</text>
      </g>
      <text className="label" x="160" y="226" textAnchor="middle" fontSize="13" fill={st === "declined" ? "var(--danger)" : st === "approved" ? "var(--ok)" : "var(--gold-text)"} fontFamily="Figtree, sans-serif" fontWeight={700}>
        {st === "locked" ? `$${c.money?.amount.toLocaleString()} locked · Guardian cannot approve · no timeout` : st === "declined" ? "Stopped by Daniel. Nothing moved." : "Both keys turned by family. Guardian turned neither."}
      </text>
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
    <svg viewBox="0 0 320 240" className={`hero ring${calling ? " calling" : ""}${live ? " live" : ""}${denied ? " denied" : ""}${confirmed ? " confirmed" : ""}`} style={{ width: "100%", height: "100%", maxHeight: 420 }} role="img" aria-label="Guardian calls the real relative on the saved number">
      <line className="dashline" x1="64" y1="140" x2="160" y2="110" stroke="#D7322A" strokeWidth="3" strokeDasharray="8 7" />
      <line className="beam" x1="160" y1="110" x2="256" y2="80" stroke="var(--accent)" strokeWidth="4" strokeLinecap="round" />
      <circle className="ripple" cx="256" cy="80" r="34" fill="none" stroke="var(--accent2)" strokeWidth="3" opacity="0" />
      <g className="caller">
        <circle r="30" fill="var(--danger-soft)" stroke="#D7322A" strokeWidth="3" strokeDasharray="7 6" />
        <text y="5" textAnchor="middle" fontSize="12" fill="var(--danger-text)" fontFamily="Figtree, sans-serif" fontWeight={700}>{c.sender ? c.sender.replace("a number ending ", "…") : "unknown"}</text>
      </g>
      <g transform="translate(160 110)"><circle r="34" fill="var(--accent)" /><text y="9" textAnchor="middle" fontSize="28" fill="#fff" fontFamily="'Young Serif', serif">{(c.protected || "A")[0]}</text></g>
      <g transform="translate(256 80)">
        <circle className="dcircle" r="30" fill="var(--page)" stroke={denied || confirmed ? "var(--ok)" : "var(--accent)"} strokeWidth="4" />
        <text y="9" textAnchor="middle" fontSize="26" fill="#161B33" fontFamily="'Young Serif', serif">D</text>
      </g>
      <circle className="pulse" r="7" fill="#fff" stroke="var(--accent2)" strokeWidth="3" />
      <g transform="translate(278 58)"><g className={`okmark${denied || confirmed ? " show" : ""}`}><circle r="12" fill="var(--ok)" /><path d="M-5 0 L-1.5 3.5 L5 -4" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /></g></g>
      <text x="64" y="196" textAnchor="middle" fontSize="12" fill="var(--muted)" fontFamily="Figtree, sans-serif">the caller</text>
      <text x="256" y="124" textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="Figtree, sans-serif">the real Daniel</text>
      <text x="256" y="137" textAnchor="middle" fontSize="10" fill="var(--muted)" fontFamily="Figtree, sans-serif">saved number</text>
      <text className="label" x="160" y="226" textAnchor="middle" fontSize="13" fill={denied ? "var(--ok)" : "var(--muted)"} fontFamily="Figtree, sans-serif" fontWeight={700}>
        {denied ? "Daniel is at work. It wasn't him." : confirmed ? "Daniel says it was him. She still waits for his direct call." : live ? "Calling Daniel on his saved number…" : calling ? "Daniel didn't pick up yet. Nothing is sent." : "Someone says they're Daniel. Guardian asks the real one."}
      </text>
    </svg>
  );
}
