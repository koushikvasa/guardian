"use client";
import { use, useRef, useState } from "react";
import { Brand } from "@/components/Logo";
import { turnKey, useGuardian } from "@/lib/guardian";

const HOLD_MS = 1500;

/** Daniel's second key. Approval needs a press-and-hold; Guardian never approves on its own. */
export default function DanielKey({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const g = useGuardian();
  const c = id === "latest" ? g.latest : g.cases[id];
  const caseId = c?.id ?? id;
  const [held, setHeld] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const state = c?.money?.state;

  const startHold = () => {
    const t0 = Date.now();
    timer.current = setInterval(() => {
      const p = Math.min(1, (Date.now() - t0) / HOLD_MS);
      setHeld(p);
      if (p >= 1) { stopHold(); turnKey(caseId, "approve"); }
    }, 30);
  };
  const stopHold = () => { if (timer.current) clearInterval(timer.current); timer.current = null; setHeld(0); };

  return (
    <main className="phone">
      <Brand size={42} />
      {!c?.money && <p style={{ marginTop: 40, color: "var(--muted)", fontSize: 18 }}>No money request is waiting for your key.</p>}
      {c?.money && (
        <>
          <div style={{ marginTop: 26, color: "var(--muted)" }}>Your mom needs your key</div>
          <h1 className="serif" style={{ fontSize: 36, lineHeight: 1.12, margin: "8px 0 0" }}>Mom wants to send ${c.money.amount.toLocaleString()}</h1>
          <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontWeight: 700 }}>What Guardian found</div>
            {(c.verdict?.fired || []).filter((f) => f.weight > 0).map((f) => (
              <div key={f.rule} style={{ fontSize: 16, lineHeight: 1.35 }}>• {f.reason_en ?? f.reason}</div>
            ))}
          </div>
          <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 12, paddingTop: 24 }}>
            {state === "locked" ? (
              <>
                <button className="btn btn-dark" style={{ minHeight: 60, fontSize: 19 }} onClick={() => turnKey(caseId, "decline")}>Don&rsquo;t send it</button>
                <button className="btn" onPointerDown={startHold} onPointerUp={stopHold} onPointerLeave={stopHold}
                  style={{ minHeight: 56, border: "2px solid var(--gold)", color: "#6B4A10", background: `linear-gradient(90deg, #F6E7C5 ${held * 100}%, transparent ${held * 100}%)` }}>
                  Press and hold to approve
                </button>
              </>
            ) : (
              <div className="card" style={{ fontWeight: 700, fontSize: 19, textAlign: "center", color: state === "declined" ? "var(--danger)" : "var(--ok)" }}>
                {state === "declined" ? "Stopped. Guardian is telling Mom in Spanish." : "Approved. Guardian told Mom."}
              </div>
            )}
            <div style={{ fontSize: 14, color: "var(--muted)", textAlign: "center" }}>Guardian tells Mom your answer in Spanish.</div>
          </div>
        </>
      )}
    </main>
  );
}
