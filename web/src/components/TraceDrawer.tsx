"use client";
import { useEffect, useMemo, useState } from "react";
import { API, CaseState, GEvent } from "@/lib/guardian";

type Span = { name: string; t0: number; dur: number; attrs: Record<string, unknown> };

const COLOR = (name: string) => name.startsWith("call.") ? "#3A4470" : name === "detonate" ? "#14705A" : name.startsWith("memory.") ? "#6B3FD1" : name.startsWith("tts") ? "#2E46E5" : name === "case" ? "#C3CBE0" : "#2E46E5";
const SPONSOR = (name: string) => name.startsWith("call.") ? "ElevenLabs" : name === "detonate" ? "Daytona · Anchor" : name.startsWith("memory.") ? "SurrealDB" : name.startsWith("tts") ? "ElevenLabs" : name === "eval.live" ? "Arize" : name === "signals.extract" ? "AWS Bedrock" : "";
const fmt = (s: number) => (s < 1 ? `${Math.round(s * 1000)} ms` : s < 60 ? `${s.toFixed(1)} s` : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`);

function fact(sp: Span): string {
  const a = sp.attrs;
  switch (sp.name) {
    case "detonate": return [a.mode, a.browser === "http" ? "no browser" : undefined, a.sandbox_id ? `sandbox ${String(a.sandbox_id).slice(0, 6)}` : undefined].filter(Boolean).join(" · ");
    case "memory.recall": return [a.tier, a.hits != null ? `${a.hits} hits` : undefined].filter(Boolean).join(" · ");
    case "rules.evaluate": return `${a.label ?? ""} ${a.score ?? ""}`.trim();
    case "signals.extract": return String(a.mode ?? "");
    case "eval.live": return Object.entries(a).filter(([k]) => ["grounded", "no_asks", "language"].includes(k)).map(([k, v]) => `${k.replace("_", " ")} ${v ? "✓" : "✗"}`).join(" · ");
    default: if (sp.name.startsWith("call.")) return [a.status, a.agent === "mock" ? "mock" : undefined].filter(Boolean).join(" · "); return "";
  }
}

/** The case's spans as a waterfall: the same spans Guardian exports to Arize, drawn on the case's own timeline. */
export function TraceDrawer({ c, onClose, modal = false }: { c: CaseState; onClose: () => void; modal?: boolean }) {
  const [fetched, setFetched] = useState<Span[] | null>(null);
  const [board, setBoard] = useState<{ overall?: { n: number; catch_rate: number; false_alarm_rate: number } } | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (c.spans && c.spans.length) return;
    fetch(`${API}/events/log`).then((r) => r.json()).then((evs: GEvent[]) => setFetched(evs.filter((e) => e.kind === "span" && e.case === c.id).map((e) => ({ name: e.name as string, t0: e.t0 as number, dur: e.dur as number, attrs: (e.attrs as Record<string, unknown>) || {} })))).catch(() => setFetched([]));
  }, [c.id, c.spans]);
  useEffect(() => { fetch(`${API}/scoreboard`).then((r) => r.json()).then(setBoard).catch(() => {}); }, []);
  const spans = useMemo(() => {
    const all = (c.spans && c.spans.length ? c.spans : fetched) || [];
    const order = ["case", "signals.extract", "detonate", "memory.recall", "rules.evaluate", "call.verify", "call.second_key", "call.warning", "tts.help_note", "herd.record", "memory.remember", "eval.live"];
    return all.slice().sort((a, b) => (order.indexOf(a.name) === -1 ? 99 : order.indexOf(a.name)) - (order.indexOf(b.name) === -1 ? 99 : order.indexOf(b.name)) || a.t0 - b.t0);
  }, [c.spans, fetched]);
  const start = spans.length ? Math.min(...spans.map((s) => s.t0)) : 0;
  const end = spans.length ? Math.max(...spans.map((s) => s.t0 + s.dur)) : 1;
  const total = Math.max(0.5, end - start);
  const sponsors = Array.from(new Set(spans.map((s) => SPONSOR(s.name)).filter(Boolean)));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * total);
  const copy = () => { if (!c.traceId) return; navigator.clipboard?.writeText(c.traceId).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); }).catch(() => {}); };

  const body = (
    <div role="dialog" aria-label={`Trace for case ${c.id}`} style={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: 18, boxShadow: "0 -18px 50px rgba(22,27,51,.22)", padding: "14px 18px 16px", display: "grid", gridTemplateColumns: "1fr 280px", gap: 18, fontSize: 13, minWidth: 0 }}>
      <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <b style={{ fontSize: 15 }}>Trace · {c.id} · {c.protected}</b>
          <span className="pill" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>sent to Arize AX</span>
          <span className="pill" style={{ background: "var(--chip)" }}>{fmt(total)} total</span>
          {c.timeToCall != null && <span className="pill" style={{ background: "var(--chip)" }}>first call in {c.timeToCall}s</span>}
          {c.status !== "closed" && <span className="pill" style={{ background: "var(--warn-soft)", color: "var(--gold-text)" }}>still running</span>}
        </span>
        <button onClick={onClose} className="pill" style={{ cursor: "pointer", border: "1px solid var(--line)", background: "var(--card)" }}>{modal ? "Close" : "T or Esc to close"}</button>
      </div>
      <div style={{ minWidth: 0 }}>
        {spans.length === 0 && <div style={{ color: "var(--muted)" }}>No spans yet for this case.</div>}
        <div style={{ display: "grid", gridTemplateColumns: "150px 1fr", gap: "5px 10px", alignItems: "center" }}>
          {spans.map((sp, i) => {
            const left = ((sp.t0 - start) / total) * 100, width = Math.max(0.4, (sp.dur / total) * 100);
            return (
              <div key={i} style={{ display: "contents" }}>
                <span style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={sp.name}>{sp.name}</span>
                <div style={{ position: "relative", height: 16, background: "var(--chip2)", borderRadius: 8 }}>
                  <i style={{ position: "absolute", top: 2, bottom: 2, left: `${left}%`, width: `${width}%`, borderRadius: 6, background: COLOR(sp.name) }} />
                  <small style={{ position: "absolute", left: `calc(${Math.min(left + width, 70)}% + 6px)`, top: 0, fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap" }}>{fmt(sp.dur)}{fact(sp) ? ` · ${fact(sp)}` : ""}{SPONSOR(sp.name) ? ` · ${SPONSOR(sp.name)}` : ""}</small>
                </div>
              </div>
            );
          })}
          {spans.length > 0 && <><span /><div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--muted)" }}>{ticks.map((t, i) => <span key={i}>{fmt(t)}</span>)}</div></>}
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
        <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase" }}>Live checks (Arize)</span>
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
          {c.evals ? Object.entries(c.evals).map(([k, ok]) => <span key={k} className="pill" style={{ background: ok ? "var(--ok-soft)" : "var(--danger-soft)", color: ok ? "var(--ok)" : "var(--danger-text)" }}>{k.replace("_", " ")} {ok ? "✓" : "✗"}</span>) : <span style={{ color: "var(--muted)" }}>run when the case closes</span>}
        </div>
        <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase" }}>Trace id</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <code style={{ fontSize: 11, background: "var(--chip2)", padding: "3px 7px", borderRadius: 6 }}>{c.traceId ? `${c.traceId.slice(0, 8)}…${c.traceId.slice(-4)}` : "not exported (rehearsal or Arize off)"}</code>
          {c.traceId && <button onClick={copy} className="pill" style={{ cursor: "pointer", border: "1px solid var(--line)", background: "var(--card)" }}>{copied ? "copied" : "copy"}</button>}
          <a href="https://app.arize.com" target="_blank" rel="noreferrer" style={{ fontWeight: 700, color: "var(--accent)" }}>Open Arize ↗</a>
        </div>
        <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase" }}>Sponsors on this case</span>
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>{["Twilio", ...sponsors].map((s) => <span key={s} className="pill" style={{ background: "var(--chip)" }}>{s}</span>)}</div>
        {board?.overall && <><span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase" }}>Offline experiment (Arize)</span>
          <div style={{ color: "var(--muted)" }}>rules-v1 · {board.overall.n} messages · catch {Math.round(board.overall.catch_rate * 100)}% · false alarms {Math.round(board.overall.false_alarm_rate * 100)}%</div></>}
      </div>
    </div>
  );

  if (modal) {
    return (
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(22,27,51,.35)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, zIndex: 50 }}>
        <div onClick={(e) => e.stopPropagation()} style={{ width: "min(1000px, 100%)" }}>{body}</div>
      </div>
    );
  }
  return <div style={{ position: "absolute", left: 28, right: 28, bottom: 58, zIndex: 30, animation: "drawerUp .5s cubic-bezier(.2,.8,.2,1) both" }}>{body}<style>{`@keyframes drawerUp { from { transform: translateY(110%); opacity: 0 } to { transform: none; opacity: 1 } }`}</style></div>;
}
