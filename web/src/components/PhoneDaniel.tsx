"use client";
import { forwardRef, useRef, useState } from "react";
import { CaseState, GEvent, LANG_NAME, turnKey } from "@/lib/guardian";
import { Mark } from "./Mark";

const HOLD_MS = 1500;

/** Daniel's phone, live: his texts from Guardian, the call captions, and the key page when money is locked. */
export const PhoneDaniel = forwardRef<HTMLDivElement, { c: CaseState | undefined; sms: GEvent[] }>(function PhoneDaniel({ c, sms }, ref) {
  const mine = c ? sms.filter((m) => m.case === c.id && m.kind === "sms.out" && m.role === "guardian") : [];
  const callKey = c ? ["second_key", "verify"].find((k) => c.calls[k]) : undefined;
  const call = callKey && c ? c.calls[callKey] : undefined;
  const live = !!call && !["completed", "no_answer", "failed"].includes(call.status);
  const keyOpen = !!c?.money && !live;
  const who = c?.protected || "Mom";
  const inLang = LANG_NAME[c?.lang || "en"] || "English";
  const [held, setHeld] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const stop = () => { if (timer.current) clearInterval(timer.current); timer.current = null; setHeld(0); };
  const start = () => {
    if (!c) return; const t0 = Date.now();
    timer.current = setInterval(() => { const p = Math.min(1, (Date.now() - t0) / HOLD_MS); setHeld(p); if (p >= 1) { stop(); turnKey(c.id, "approve"); } }, 30);
  };
  const state = c?.money?.state;

  return (
    <div className="phone2" ref={ref}>
      <div className="bar"><Mark size={34} tilt={false} /><div>Guardian<small>Daniel&rsquo;s phone</small></div></div>
      <div className="thread">
        {mine.length === 0 && <div className="msg g" style={{ opacity: 0.6 }}><span className="k">Guardian</span>Nothing needs you.</div>}
        {mine.map((m, i) => <div key={i} className="msg g alert" style={m.delivered === false ? { opacity: 0.55 } : undefined}><span className="k">Guardian</span>{String(m.body ?? "").replace(/^Guardian: /, "")}</div>)}
        {call && (
          <div className="msg" style={{ alignSelf: "stretch", maxWidth: "100%", background: "var(--ink)", color: "#fff" }}>
            <span className="k" style={{ color: "#B9C0DA" }}>{callKey === "verify" ? "Guardian is calling you" : "Guardian is calling you about the money"}{live ? " · on the line" : ""}</span>
            {live && call.lines.length === 0 && <div className="wave" aria-hidden="true">{Array.from({ length: 14 }).map((_, i) => <i key={i} />)}</div>}
            {call.lines.slice(-3).map((l, i) => <div key={i} className="serif" style={{ fontSize: 15, marginTop: 4, color: l.role === "user" ? "#9EB0FF" : "#fff" }}>{l.text}</div>)}
          </div>
        )}
      </div>
      <div className={`callover${live ? " show" : ""}`} aria-live="polite">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}><Mark size={44} tilt={false} mood="calling" /><div style={{ fontWeight: 700 }}>Guardian<small style={{ display: "block", color: "#B9C0DA", fontWeight: 500 }}>{call?.status === "connected" ? "On the call" : "Calling…"}</small></div></div>
        <div className="cap now">{callKey === "verify" ? `Did you contact ${who} today asking for help or money?` : `${who} wants to send $${c?.money?.amount.toLocaleString()} by ${c?.money?.method}. Do you want her to send it?`}</div>
        <div style={{ fontSize: 13, color: "#B9C0DA" }}>{callKey === "verify" ? "One question, on your saved number." : "A spoken yes is never enough. Approval needs your press-and-hold."}</div>
        <div className="wave" aria-hidden="true">{Array.from({ length: 16 }).map((_, i) => <i key={i} />)}</div>
      </div>
      <div className={`keypane${keyOpen ? " show" : ""}`}>
        {c?.money && (
          <>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>{who} needs your key</div>
            <h3 className="serif" style={{ fontWeight: 400, fontSize: 26, lineHeight: 1.1, margin: 0 }}>{who} wants to send ${c.money.amount.toLocaleString()}</h3>
            <div style={{ fontSize: 14, display: "flex", flexDirection: "column", gap: 4 }}>
              {(c.verdict?.fired || []).filter((f) => f.weight > 0 && f.rule !== "remembered_scam").slice(0, 3).map((f) => <div key={f.rule}>• {f.reason_en ?? f.reason}</div>)}
            </div>
            {c.memory && c.memory.hits.length > 0 && <div className="mem" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Guardian remembers: {c.memory.hits[0].text.replace(/^On \d{4}-\d{2}-\d{2}, /, "")}</div>}
            {state === "locked" ? (
              <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
                <button className="btn btn-dark" style={{ minHeight: 48, fontSize: 16 }} onClick={() => c && turnKey(c.id, "decline")}>Don&rsquo;t send it</button>
                <button className="btn" onPointerDown={start} onPointerUp={stop} onPointerLeave={stop} onPointerCancel={stop}
                  style={{ minHeight: 46, border: "2px solid var(--gold)", color: "#6B4A10", background: `linear-gradient(90deg, #F6E7C5 ${held * 100}%, transparent ${held * 100}%)`, touchAction: "none" }}>
                  Press and hold to approve
                </button>
              </div>
            ) : (
              <div style={{ marginTop: "auto", fontWeight: 700, fontSize: 17, textAlign: "center", color: state === "declined" ? "var(--danger)" : "var(--ok)" }}>
                {state === "declined" ? `Stopped. Guardian is telling ${who} in ${inLang}.` : `Approved. Guardian told ${who}.`}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
});
