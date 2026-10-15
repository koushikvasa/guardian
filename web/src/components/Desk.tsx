"use client";
import { useEffect, useRef, useState } from "react";
import { API, CaseState, LANG_NAME } from "@/lib/guardian";
import { Mark, Mood, Look } from "./Mark";

const LABEL: Record<string, string> = { scam: "SCAM", suspicious: "SUSPICIOUS", safe: "SAFE" };
const LABEL_COLOR: Record<string, string> = { scam: "var(--danger)", suspicious: "#6B4A10", safe: "var(--ok)" };

type StepKey = "recv" | "check" | "verdict" | "call" | "teach" | "help" | "rem";
type Step = { key: StepKey; title: string; state: "done" | "now" | "todo"; ts?: string; keep?: boolean };

function fmt(s: number | null | undefined) { return s == null ? "" : s < 60 ? `${s.toFixed(1)} s` : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`; }

/** Which call is the case's main one right now (verify / second_key before warning). */
export function mainCall(c: CaseState) {
  const k = ["second_key", "verify", "warning"].find((x) => c.calls[x] && !["completed", "no_answer", "failed"].includes(c.calls[x].status))
    || ["warning", "second_key", "verify"].find((x) => c.calls[x]);
  return k ? { key: k, call: c.calls[k] } : null;
}

export function moodFor(c: CaseState | undefined): Mood {
  if (!c) return "idle";
  const mc = mainCall(c);
  if (mc && !["completed", "no_answer", "failed"].includes(mc.call.status)) return "calling";
  if (c.status === "closed") return c.verdict?.label === "scam" ? "safe" : "safe";
  if (c.verdict) return c.verdict.label === "scam" ? "scam" : c.verdict.label === "suspicious" ? "suspicious" : "safe";
  if (c.detonation || c.text?.match(/https?:|\.[a-z]{2,}\//)) return "suspicious";
  return "reading";
}

export function narration(c: CaseState | undefined, who: string): string {
  if (!c) return "Watching. Nothing to do.";
  const mc = mainCall(c);
  const live = mc && !["completed", "no_answer", "failed"].includes(mc.call.status);
  if (live) return mc.key === "verify" ? "Calling the real Daniel on his saved number." : mc.key === "second_key" ? "Calling Daniel. I can't approve this; only he can." : `On the line with ${who}, in ${LANG_NAME[c.lang || "en"]}, with the family phrase.`;
  if (c.status === "closed") return c.verdict?.label === "scam" ? "Remembered. Next time this shows up, I already know." : "Looked safe. I said nothing.";
  if (c.help) return `${who} knows what to do next time.`;
  if (c.teachback != null) return c.teachback ? `${who} said it back correctly.` : `I explained once more.`;
  if (c.money?.state === "locked") return `$${c.money.amount.toLocaleString()} is locked until Daniel turns the key.`;
  if (c.money?.state === "declined") return "Stopped by Daniel. Nothing moved.";
  if (c.money?.state === "approved") return "Daniel turned the key. She may go ahead.";
  if (c.verify === "denied") return "Daniel says it wasn't him. Telling her now.";
  if (c.verdict) return c.verdict.label === "scam" ? `Scam. ${c.verdict.fired.filter((f) => f.weight > 0).length} rules fired. Calling now.` : c.verdict.label === "suspicious" ? "Doesn't add up. Telling her not to touch it." : "Looks safe.";
  if (c.detonation) return "Opened the link where it can't hurt anyone.";
  if (c.text?.match(/https?:|\.[a-z]{2,}\//)) return "There's a link. Opening it in a sandbox.";
  return `A text landed on ${who}'s phone. Reading it.`;
}

export function steps(c: CaseState): Step[] {
  const mc = mainCall(c);
  const callDone = mc && ["completed", "no_answer", "failed"].includes(mc.call.status);
  const hasLink = !!(c.detonation || c.text?.match(/https?:|\.[a-z]{2,}\//));
  const s: Step[] = [
    { key: "recv", title: "Received", state: "done", ts: "0.0 s" },
    { key: "check", title: hasLink ? "Opened the link in a sandbox" : "Read the story", state: c.detonation || c.verdict ? "done" : "now", ts: c.detonation ? fmt(Number(c.detonation.elapsed_s) || undefined) : undefined, keep: !!c.detonation },
    { key: "verdict", title: c.money ? `Verdict · $${c.money.amount.toLocaleString()} locked` : "Verdict", state: c.verdict ? "done" : "todo", keep: true },
    { key: "call", title: mc ? (mc.key === "verify" ? "Calling the real Daniel" : mc.key === "second_key" ? "Calling Daniel for the key" : `Calling ${c.protected || "her"}, in ${LANG_NAME[c.lang || "en"]}`) : "Call", state: callDone ? "done" : mc ? "now" : "todo", ts: c.timeToCall != null ? fmt(c.timeToCall) : undefined, keep: true },
    { key: "teach", title: "Teach-back", state: c.teachback != null ? "done" : "todo", keep: true },
    { key: "help", title: "Help note for her friends", state: c.help ? "done" : "todo", keep: true },
    { key: "rem", title: "Remembered", state: c.status === "closed" ? "done" : "todo", keep: true },
  ];
  if (c.status !== "closed" && !s.some((x) => x.state === "now")) { const i = s.findIndex((x) => x.state === "todo"); if (i > 0) s[i].state = "now"; }
  return s;
}

export function Desk({ c, who, lookAt }: { c: CaseState | undefined; who: string; lookAt: Look }) {
  const mood = moodFor(c);
  const say = narration(c, who);
  const [stampOn, setStampOn] = useState(false);
  const stampRef = useRef<string | null>(null);
  useEffect(() => {
    const key = c ? `${c.id}:${c.verdict?.label ?? ""}` : "";
    if (c?.verdict && stampRef.current !== key) { stampRef.current = key; setStampOn(false); const t = setTimeout(() => setStampOn(true), 40); return () => clearTimeout(t); }
    if (!c?.verdict) setStampOn(false);
  }, [c]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <Mark size={96} mood={mood} look={lookAt} />
        <div className="serif" style={{ fontSize: 26, lineHeight: 1.2, minHeight: "2.4em" }} aria-live="polite">{say}</div>
      </div>
      {c && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {steps(c).map((s) => (
            <div key={s.key} className={`step ${s.state}${s.keep ? " keep" : ""}`}>
              <span className="dot" />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700 }}>{s.title}</div>
                <div className="body">{body(s.key, c, stampOn)}</div>
              </div>
              <span className="ts">{s.ts || ""}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function body(k: StepKey, c: CaseState, stampOn: boolean) {
  const d = c.detonation;
  switch (k) {
    case "recv":
      return <span style={{ color: "var(--muted)" }}>From {c.sender || "an unknown number"} · {c.quiet ? `auto-forwarded, ${c.protected} touched nothing` : "forwarded by " + (c.protected || "her")} · {LANG_NAME[c.lang || "en"]}</span>;
    case "check":
      if (!d) return <span style={{ color: "var(--muted)" }}>{c.verdict ? "No link. Judged on the story." : "Working…"}</span>;
      return (
        <div className={`sand${d.sandbox_destroyed_s != null ? " gone" : ""}`}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, color: "var(--danger)", fontWeight: 600, overflowWrap: "anywhere" }}>{String(d.final_domain || "")}</div>
            {Array.isArray(d.form_fields) && d.form_fields.length > 0 && <div style={{ fontSize: 13 }}>Asks for: {d.form_fields.join(" · ")}</div>}
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
              {d.browser === "http" ? "Fetched without a browser" : "Anchor Browser opened it"} · parsed inside Daytona sandbox {String(d.sandbox_id || "").slice(0, 6)}
              {d.domain_age_days != null ? ` · domain ${d.domain_age_days} days old` : ""} · <b style={{ color: "var(--ok)" }}>{d.sandbox_destroyed_s != null ? `destroyed in ${d.sandbox_destroyed_s} s` : "destroying…"}</b>
            </div>
          </div>
          {d.screenshot_url ? <img src={`${API}${d.screenshot_url}`} alt="" className="pg" style={{ objectFit: "cover", objectPosition: "top" }} /> : <div className="pg" aria-hidden="true"><i className="h" /><i /><i /><i /><i style={{ background: "#23408E" }} /></div>}
        </div>
      );
    case "verdict": {
      const v = c.verdict; if (!v) return null;
      return (
        <div>
          <span className={`stamp${stampOn ? " show" : ""}`} style={{ borderColor: LABEL_COLOR[v.label], color: LABEL_COLOR[v.label] }}>{LABEL[v.label]} · {v.score}</span>
          {v.fired.filter((f) => f.weight > 0).map((f, i) => (
            <div key={f.rule} className="reason show" style={{ transitionDelay: `${i * 120}ms` }}><i>{i + 1}</i><span>{f.reason} <small>· {f.rule}</small></span></div>
          ))}
          {c.memory && c.memory.hits.length > 0 && <div className="mem" style={{ marginTop: 8 }}>Guardian remembers: {c.memory.hits[0].text}{c.memory.trace_id ? ` · SurrealDB trace ${c.memory.trace_id.slice(0, 8)}` : ""}</div>}
          {c.money && <div style={{ marginTop: 8, fontSize: 13, color: "var(--muted)" }}>Money is locked. Guardian cannot approve. No timeout. {c.money.state === "declined" ? "Stopped by Daniel." : c.money.state === "approved" ? "Approved by Daniel." : "Waiting for Daniel's key."}</div>}
        </div>
      );
    }
    case "call": {
      const mc = mainCall(c); if (!mc) return null;
      const live = !["completed", "no_answer", "failed"].includes(mc.call.status);
      if (live) return <span style={{ color: "var(--muted)" }}>{mc.call.status === "connected" ? "On the line. Captions arrive when the call ends." : "Ringing…"}</span>;
      const lines = mc.call.lines.slice(-3);
      return <div className="serif" style={{ fontSize: 17, lineHeight: 1.3 }}>{lines.length ? lines.map((l, i) => <div key={i} style={{ color: l.role === "user" ? "var(--accent)" : "inherit" }}>{l.text}</div>) : <span style={{ color: "var(--muted)" }}>{mc.call.status.replace("_", " ")}</span>}{c.verify && <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 4 }}>Daniel: {c.verify}</div>}</div>;
    }
    case "teach":
      return c.teachback == null ? null : <span>{c.teachback ? "Passed · she said it back correctly" : "Explained once more"}</span>;
    case "help":
      return c.help ? <span>“{c.help.title}” · {c.help.steps.length} lines{c.help.audio_url ? " · 20 s audio" : ""} · sent</span> : null;
    case "rem":
      return c.status === "closed" ? <span>Agent Memory + herd fingerprints{c.evals ? ` · Arize: ${Object.entries(c.evals).map(([k, ok]) => `${k.replace("_", " ")} ${ok ? "✓" : "✗"}`).join(" · ")}` : ""}</span> : null;
  }
}
