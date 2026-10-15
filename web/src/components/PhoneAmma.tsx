"use client";
import { forwardRef, useEffect, useState } from "react";
import { CaseState, GEvent } from "@/lib/guardian";
import { Mark } from "./Mark";

const UI: Record<string, { calling: string; phrase: string; onCall: string }> = {
  en: { calling: "Calling…", phrase: "Family phrase", onCall: "On the call" },
  te: { calling: "కాల్ చేస్తోంది…", phrase: "కుటుంబ పదం", onCall: "కాల్ జరుగుతోంది" },
  es: { calling: "Llamando…", phrase: "Frase de familia", onCall: "En llamada" },
};

/** The protected member's phone, live: her thread with Guardian, and the call takeover while Guardian calls her. */
export const PhoneAmma = forwardRef<HTMLDivElement, { c: CaseState | undefined; sms: GEvent[]; who: string; phrase?: string }>(function PhoneAmma({ c, sms, who, phrase }, ref) {
  const lang = c?.lang || "en";
  const ui = UI[lang] || UI.en;
  const call = c?.calls?.warning;
  const live = !!call && !["completed", "no_answer", "failed"].includes(call.status);
  const [linger, setLinger] = useState(false);
  const [secs, setSecs] = useState(0);
  useEffect(() => { if (live) { setSecs(0); const t = setInterval(() => setSecs((s) => s + 1), 1000); return () => clearInterval(t); } }, [live, c?.id]);
  useEffect(() => { if (call && !live && call.lines.length) { setLinger(true); const t = setTimeout(() => setLinger(false), 9000); return () => clearTimeout(t); } }, [call, live]);
  const show = live || linger;
  const mine = (c ? sms.filter((m) => m.case === c.id && m.kind === "sms.out" && m.role !== "guardian") : []);

  return (
    <div className="phone2" ref={ref} lang={lang}>
      <div className="bar"><Mark size={34} tilt={false} /><div>Guardian<small>{who}&rsquo;s phone</small></div></div>
      <div className="thread">
        {c?.text && <div className="msg in"><span className="k">{c.sender || "Unknown number"}</span>{c.text}</div>}
        {mine.map((m, i) => (
          <div key={i} className={`msg g${m.key === "scam_calling" || m.key === "verify_denied" || m.key === "key_declined" ? " alert" : ""}`} style={m.delivered === false ? { opacity: 0.55 } : undefined}>
            <span className="k">Guardian{m.delivered === false ? " · shown on screen" : ""}</span>{String(m.body ?? "").replace(/^Guardian: /, "")}
          </div>
        ))}
        {!c && <div style={{ color: "var(--muted)", fontSize: 14, textAlign: "center", padding: 20 }}>Nothing yet.</div>}
      </div>
      <div className={`callover${show ? " show" : ""}`} aria-live="polite">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}><Mark size={44} tilt={false} mood="calling" /><div style={{ fontWeight: 700 }}>Guardian<small style={{ display: "block", color: "#B9C0DA", fontWeight: 500 }}>{live ? (call?.status === "connected" ? `${ui.onCall} · 0:${String(secs).padStart(2, "0")}` : ui.calling) : "Call ended"}</small></div></div>
        {phrase && <div className="phrase">{ui.phrase}: <b>“{phrase}”</b></div>}
        {call?.lines.slice(-4).map((l, i, arr) => <div key={i} className={`cap${i === arr.length - 1 ? " now" : ""}${l.role === "user" ? " user" : ""}`}>{l.text}</div>)}
        {live && <div className="wave" aria-hidden="true">{Array.from({ length: 16 }).map((_, i) => <i key={i} />)}</div>}
      </div>
    </div>
  );
});
