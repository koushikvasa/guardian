"use client";
import { useEffect, useRef, useState } from "react";
import { API, CaseState, LANG_NAME } from "@/lib/guardian";
import { Mark, Mood, Look } from "./Mark";

const LABEL: Record<string, string> = { scam: "SCAM", suspicious: "SUSPICIOUS", safe: "SAFE" };
const LABEL_COLOR: Record<string, string> = { scam: "var(--danger)", suspicious: "#6B4A10", safe: "var(--ok)" };
const ENDED = ["completed", "no_answer", "failed"];

type StepKey = "recv" | "check" | "verdict" | "call" | "teach" | "help" | "rem";
type Step = { key: StepKey; title: string; state: "done" | "now" | "todo"; ts?: string; result?: string };

const fmt = (s: number | null | undefined) => (s == null ? "" : s < 60 ? `${s.toFixed(1)} s` : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`);
const hasLink = (c: CaseState) => !!(c.detonation || c.text?.match(/https?:|\.[a-z]{2,}\//));

/** The case's main call right now: an active verify / second_key / warning, else the last one that ran. */
export function mainCall(c: CaseState) {
  const k = ["second_key", "verify", "warning"].find((x) => c.calls[x] && !ENDED.includes(c.calls[x].status)) || ["warning", "second_key", "verify"].find((x) => c.calls[x]);
  return k ? { key: k, call: c.calls[k], live: !ENDED.includes(c.calls[k].status) } : null;
}

export function moodFor(c: CaseState | undefined): Mood {
  if (!c) return "idle";
  const mc = mainCall(c);
  if (mc?.live) return "calling";
  if (c.status === "closed") return "safe";
  if (c.verdict) return c.verdict.label === "scam" ? "scam" : c.verdict.label === "suspicious" ? "suspicious" : "safe";
  if (hasLink(c)) return "suspicious";
  return "reading";
}

export function narration(c: CaseState | undefined, who: string): string {
  if (!c) return "Watching. Nothing to do.";
  const mc = mainCall(c);
  if (mc?.live) return mc.key === "verify" ? "Calling the real Daniel on his saved number." : mc.key === "second_key" ? "Calling Daniel. I can't approve this; only he can." : `On the line with ${who}, in ${LANG_NAME[c.lang || "en"]}, with the family phrase.`;
  if (c.status === "closed") return c.verdict?.label === "scam" ? "Remembered. Next time this shows up, I already know." : "Looked safe. I said nothing.";
  if (c.help) return `${who} knows what to do next time.`;
  if (c.teachback != null) return c.teachback ? `${who} said it back correctly.` : "I explained once more.";
  if (c.money?.state === "locked") return `$${c.money.amount.toLocaleString()} is locked until Daniel turns the key.`;
  if (c.money?.state === "declined") return "Stopped by Daniel. Nothing moved.";
  if (c.money?.state === "approved") return "Daniel turned the key. She may go ahead.";
  if (c.verify === "denied") return "Daniel says it wasn't him. Telling her now.";
  if (c.verdict) return c.verdict.label === "scam" ? `Scam. ${c.verdict.fired.filter((f) => f.weight > 0).length} rules fired. Calling now.` : c.verdict.label === "suspicious" ? "Doesn't add up. Telling her not to touch it." : "Looks safe.";
  if (c.detonation) return "Opened the link where it can't hurt anyone.";
  if (hasLink(c)) return "There's a link. Opening it in a sandbox.";
  return `A text landed on ${who}'s phone. Reading it.`;
}

export function steps(c: CaseState): Step[] {
  const mc = mainCall(c);
  const d = c.detonation;
  const s: Step[] = [
    { key: "recv", title: "Received", state: "done", ts: "0.0 s", result: c.quiet ? "auto-forwarded" : "forwarded" },
    { key: "check", title: hasLink(c) ? "Opened in a sandbox" : "Read the story", state: d || c.verdict ? "done" : "now", ts: d ? fmt(Number(d.elapsed_s) || undefined) : undefined, result: d ? (d.sandbox_destroyed_s != null ? `destroyed in ${d.sandbox_destroyed_s} s` : "parsed") : c.verdict ? "no link" : undefined },
    { key: "verdict", title: "Verdict", state: c.verdict ? "done" : "todo", result: c.verdict ? `${c.verdict.label} · ${c.verdict.score}${c.money ? ` · $${c.money.amount.toLocaleString()} ${c.money.state}` : ""}` : undefined },
    { key: "call", title: mc ? (mc.key === "verify" ? "Called the real Daniel" : mc.key === "second_key" ? "Called Daniel for the key" : `Called ${c.protected || "her"}`) : "Call", state: mc ? (mc.live ? "now" : "done") : "todo", ts: c.timeToCall != null ? fmt(c.timeToCall) : undefined, result: mc ? (mc.live ? mc.call.status : c.verify ? `Daniel: ${c.verify}` : mc.call.status.replace("_", " ")) : undefined },
    { key: "teach", title: "Teach-back", state: c.teachback != null ? "done" : "todo", result: c.teachback == null ? undefined : c.teachback ? "passed" : "repeated once" },
    { key: "help", title: "Help note", state: c.help ? "done" : "todo", result: c.help ? "sent" : undefined },
    { key: "rem", title: "Remembered", state: c.status === "closed" ? "done" : "todo", result: c.status === "closed" ? "memory + herd" : undefined },
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
  const list = c ? steps(c) : [];
  const now = list.find((s) => s.state === "now")?.key;

  return (
    <div style={{ display: "grid", gridTemplateRows: "auto minmax(0, 1fr)", gap: 12, minWidth: 0, height: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <Mark size={80} mood={mood} look={lookAt} />
        <div className="serif" style={{ fontSize: 22, lineHeight: 1.2, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }} aria-live="polite">{say}</div>
      </div>
      {c && (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(200px, 270px) 1fr", gap: 16, minHeight: 0 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 2, minHeight: 0, overflow: "hidden" }}>
            {list.map((s) => (
              <div key={s.key} className={`step ${s.state}`}>
                <span className="dot" />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 14, lineHeight: 1.2 }}>{s.title}</div>
                  {s.result && <div style={{ fontSize: 11.5, color: "var(--muted)", overflowWrap: "anywhere", lineHeight: 1.25 }}>{s.result}</div>}
                </div>
                <span className="ts">{s.ts || ""}</span>
              </div>
            ))}
          </div>
          <div className="card" style={{ minWidth: 0, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column", gap: 10 }}>
            {focus(c, now, stampOn)}
          </div>
        </div>
      )}
    </div>
  );
}

/** The focus card: the current step in detail; after the case closes, the verdict with its reasons. */
function focus(c: CaseState, now: StepKey | undefined, stampOn: boolean) {
  const d = c.detonation;
  const key: StepKey = c.status === "closed" ? "verdict" : now && now !== "recv" ? now : c.verdict ? "verdict" : "check";
  const head = (t: string) => <div style={{ fontSize: 12, letterSpacing: ".08em", textTransform: "uppercase", fontWeight: 700, color: "var(--muted)" }}>{t}</div>;

  if (key === "check") {
    if (!d) return <>{head(hasLink(c) ? "Opening the link in a sandbox" : "Reading the story")}<div style={{ color: "var(--muted)" }}>{hasLink(c) ? "The page is fetched, then parsed inside a throwaway Daytona sandbox with no network." : "No link. Guardian reads who is claiming what, and what they want."}</div></>;
    return (
      <>
        {head("Inside the sandbox")}
        <div className={`sand${d.sandbox_destroyed_s != null ? " gone" : ""}`}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 15, color: "var(--danger)", fontWeight: 700, overflowWrap: "anywhere" }}>{String(d.final_domain || "")}</div>
            {d.title ? <div style={{ fontSize: 14 }}>{String(d.title)}</div> : null}
            {Array.isArray(d.form_fields) && d.form_fields.length > 0 && <div style={{ fontSize: 14, marginTop: 4 }}>Asks for: <b>{d.form_fields.join(" · ")}</b></div>}
            <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 8 }}>
              {d.browser === "http" ? "Fetched without a browser" : "Anchor Browser opened it"} · parsed inside Daytona sandbox {String(d.sandbox_id || "").slice(0, 6)}{d.domain_age_days != null ? ` · domain ${d.domain_age_days} days old` : ""}
              <div style={{ color: "var(--ok)", fontWeight: 700, marginTop: 2 }}>{d.sandbox_destroyed_s != null ? `Sandbox destroyed in ${d.sandbox_destroyed_s} s` : "Destroying the sandbox…"}</div>
            </div>
          </div>
          {d.screenshot_url ? <img src={`${API}${d.screenshot_url}`} alt="" className="pg" style={{ objectFit: "cover", objectPosition: "top" }} /> : <div className="pg" aria-hidden="true"><i className="h" /><i /><i /><i /><i style={{ background: "#23408E" }} /></div>}
        </div>
      </>
    );
  }
  if (key === "verdict" || !c.verdict) {
    const v = c.verdict;
    if (!v) return <>{head("Deciding")}<div style={{ color: "var(--muted)" }}>Rules only. The model extracts signals; it never decides.</div></>;
    return (
      <>
        {head(c.status === "closed" ? "What didn't add up" : "Verdict")}
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span className={`stamp${stampOn ? " show" : ""}`} style={{ borderColor: LABEL_COLOR[v.label], color: LABEL_COLOR[v.label], margin: 0 }}>{LABEL[v.label]} · {v.score}</span>
          {c.money && <span className="pill" style={{ background: c.money.state === "locked" ? "#F6E7C5" : c.money.state === "declined" ? "#FCE4E2" : "#DDF3EA", color: c.money.state === "locked" ? "#6B4A10" : c.money.state === "declined" ? "#8C1D18" : "var(--ok)" }}>${c.money.amount.toLocaleString()} · {c.money.state === "locked" ? "locked, waiting for Daniel's key" : c.money.state === "declined" ? "stopped by Daniel" : "approved by Daniel"}</span>}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, overflow: "hidden" }}>
          {v.fired.filter((f) => f.weight > 0 && f.rule !== "remembered_scam").slice(0, 4).map((f, i) => (
            <div key={f.rule} className="reason show" style={{ transitionDelay: `${i * 120}ms`, fontSize: 15 }}><i>{i + 1}</i><span>{f.reason} <small>· {f.rule}</small></span></div>
          ))}
        </div>
        {c.memory && c.memory.hits.length > 0 && <div className="mem" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={c.memory.hits[0].text}>Guardian remembers · {c.memory.hits[0].when}: {c.memory.hits[0].text.replace(/^On \d{4}-\d{2}-\d{2}, /, "")}{c.memory.trace_id ? ` · trace ${c.memory.trace_id.slice(0, 6)}` : ""}</div>}
        {c.status === "closed" && c.evals && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: "auto" }}>{Object.entries(c.evals).map(([k, ok]) => <span key={k} className="pill" style={{ background: ok ? "#DDF3EA" : "#FCE4E2" }}>Arize · {k.replace("_", " ")} {ok ? "✓" : "✗"}</span>)}{c.teachback != null && <span className="pill" style={{ background: "#E4E8F1" }}>teach-back {c.teachback ? "passed" : "repeated"}</span>}</div>}
      </>
    );
  }
  if (key === "call") {
    const mc = mainCall(c); if (!mc) return null;
    const toWhom = mc.key === "warning" ? (c.protected || "her") : "Daniel";
    return (
      <>
        {head(mc.live ? `On the line with ${toWhom}` : `Call to ${toWhom} ended`)}
        <div className="serif" style={{ fontSize: 22, lineHeight: 1.25 }}>{mc.live ? (mc.call.status === "connected" ? "Connected. Watch the phone for the captions." : "Ringing…") : c.verify ? `Daniel: ${c.verify}.` : mc.call.status.replace("_", " ")}</div>
        <div style={{ color: "var(--muted)", fontSize: 14 }}>{mc.key === "warning" ? `Says the family phrase first, then two reasons in ${LANG_NAME[c.lang || "en"]}, then asks her what she will do next time.` : mc.key === "verify" ? "One question, on his saved number: did you contact her today?" : "Explains what was asked and why it looks wrong. A spoken yes is never enough: approval needs his press-and-hold."}</div>
        {c.money && <div style={{ marginTop: "auto", fontSize: 13, color: "var(--muted)" }}>Money stays locked until Daniel's key. Guardian cannot approve. No timeout.</div>}
      </>
    );
  }
  if (key === "teach") return <>{head("Teach-back")}<div className="serif" style={{ fontSize: 22 }}>{c.teachback ? "She said it back correctly." : "Explained once more and asked again."}</div></>;
  if (key === "help") return <>{head("Help note for her friends")}{c.help && <><div className="serif" style={{ fontSize: 22 }}>“{c.help.title}”</div>{c.help.steps.map((s, i) => <div key={i} style={{ fontSize: 14 }}>{i + 1}. {s}</div>)}{c.help.audio_url && <audio controls preload="none" src={`${API}${c.help.audio_url}`} style={{ width: "100%" }} />}</>}</>;
  return <>{head("Remembering")}<div style={{ color: "var(--muted)" }}>Verdict into SurrealDB Agent Memory, fingerprints into the herd graph, trace to Arize.</div></>;
}
