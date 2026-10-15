"use client";
import { useEffect, useMemo, useState } from "react";
import { Brand } from "@/components/Logo";
import { API, CaseState, fireDemo, Lang, LANG_NAME, useGuardian } from "@/lib/guardian";

const LABEL: Record<string, { text: string; color: string; bg: string }> = {
  scam: { text: "Scam", color: "#fff", bg: "var(--danger)" },
  suspicious: { text: "Suspicious", color: "#6B4A10", bg: "#FFF3D6" },
  safe: { text: "Safe", color: "#fff", bg: "var(--ok)" },
};
const PROTECTED: Record<Lang, string> = { en: "Jasmine", te: "Amma", es: "Rosa" };
const CALL_TITLE: Record<string, (c: CaseState) => string> = {
  verify: () => "Calling the real Daniel",
  second_key: () => "Second key call to Daniel",
  warning: (c) => `Warning call to ${c.protected || "her"}`,
};
const BEATS: { key: "link" | "family" | "money" | "support"; hot: string; label: string }[] = [
  { key: "link", hot: "1", label: "bank link" },
  { key: "family", hot: "2", label: "“it’s Daniel”" },
  { key: "money", hot: "3", label: "$2,000 wire" },
  { key: "support", hot: "4", label: "“Microsoft” call" },
];

type Step = { name: string; state: "done" | "active" | "todo"; note?: string };

function steps(c: CaseState): Step[] {
  const v = c.verdict;
  const callK = ["verify", "second_key", "warning"].find((k) => c.calls[k]);
  const call = callK ? c.calls[callK] : undefined;
  const callDone = call && ["completed", "no_answer", "failed"].includes(call.status);
  const s: Step[] = [
    { name: "Received", state: "done" },
    { name: "Checked", state: c.detonation || v ? "done" : "active", note: c.detonation ? "in a sandbox" : c.text?.includes("http") || c.text?.includes(".") ? "opening link" : "reading" },
    { name: "Verdict", state: v ? "done" : "todo", note: v ? LABEL[v.label].text : undefined },
    { name: "Call", state: callDone ? "done" : call ? "active" : "todo", note: call ? (callDone ? call.status.replace("_", " ") : call.status) : undefined },
    { name: "Teach-back", state: c.teachback != null ? "done" : "todo", note: c.teachback == null ? undefined : c.teachback ? "passed" : "repeated" },
    { name: "Help note", state: c.help ? "done" : "todo" },
    { name: "Remembered", state: c.status === "closed" ? "done" : "todo" },
  ];
  const firstTodo = s.findIndex((x) => x.state === "todo");
  if (c.status !== "closed" && firstTodo > 0 && !s.some((x) => x.state === "active")) s[firstTodo].state = "active";
  return s;
}

/** The projector screen. Keys 1–4 fire the demo beats in the selected language; L cycles the language. */
export default function Stage() {
  const { latest: c, connected } = useGuardian();
  const [lang, setLang] = useState<Lang>("en");
  const [texts, setTexts] = useState<{ sent: number; budget: number | null } | null>(null);
  const v = c?.verdict;
  const d = c?.detonation;

  useEffect(() => {
    const tick = () => fetch(`${API}/health`).then((r) => r.json()).then((h) => setTexts(h.texts)).catch(() => {});
    tick();
    const id = setInterval(tick, 8000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      const beat = BEATS.find((b) => b.hot === e.key);
      if (beat) fireDemo(beat.key, lang);
      if (e.key.toLowerCase() === "l") setLang((l) => (l === "en" ? "te" : l === "te" ? "es" : "en"));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lang]);

  const rail = useMemo(() => (c ? steps(c) : []), [c]);
  const callOrder = ["verify", "second_key", "warning"];

  return (
    <main style={{ minHeight: "100vh", padding: "28px 48px 24px", display: "grid", gridTemplateRows: "auto 1fr auto", gap: 18 }}>
      {/* header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Brand size={44} />
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {(["en", "te", "es"] as Lang[]).map((l) => (
            <button key={l} className="pill" onClick={() => setLang(l)}
              style={{ cursor: "pointer", border: "1px solid var(--line)", background: lang === l ? "var(--ink)" : "#fff", color: lang === l ? "#fff" : "var(--ink)" }}>
              {PROTECTED[l]} · {LANG_NAME[l]}
            </button>
          ))}
          <span style={{ width: 10 }} />
          {BEATS.map((b) => (
            <button key={b.key} className="pill" onClick={() => fireDemo(b.key, lang)} style={{ cursor: "pointer", border: "1px solid var(--line)", background: "#fff" }}>
              <b style={{ color: "var(--accent)" }}>{b.hot}</b> {b.label}
            </button>
          ))}
          <span style={{ width: 10 }} />
          <span className="pill" style={{ background: connected ? "#DDF3EA" : "#FCE4E2" }}>{connected ? "live" : "reconnecting"}</span>
        </div>
      </div>

      {/* body */}
      {!c ? (
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 18, maxWidth: 900 }}>
          <h1 className="serif" style={{ fontSize: 64, lineHeight: 1.06, margin: 0 }}>{PROTECTED[lang]} doesn&rsquo;t forward anything. Her phone does, and her family answers.</h1>
          <p style={{ fontSize: 22, color: "var(--muted)", margin: 0, lineHeight: 1.45 }}>
            Text {PROTECTED[lang]}&rsquo;s phone from any number, or press <b>1</b>–<b>4</b> to fire a demo beat in {LANG_NAME[lang]}.
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1.05fr 1fr", gap: 36, alignItems: "start" }}>
          {/* left: the story */}
          <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ color: "var(--muted)", fontWeight: 600, fontSize: 15 }}>
              Case {c.id} · {c.protected}&rsquo;s phone · {LANG_NAME[c.lang || "en"]}
            </div>
            <div className="card" style={{ borderRadius: "4px 20px 20px 20px", fontSize: 21, lineHeight: 1.4 }} lang={c.lang}>{c.text}</div>
            {v ? (
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <span className="pill" style={{ fontSize: 24, padding: "8px 20px", background: LABEL[v.label].bg, color: LABEL[v.label].color }}>{LABEL[v.label].text}</span>
                <span style={{ color: "var(--muted)", fontSize: 18 }}>score {v.score}</span>
                {c.verify && <span className="pill" style={{ background: "#E4E8F1" }}>Daniel: {c.verify}</span>}
              </div>
            ) : (
              <div style={{ color: "var(--muted)", fontSize: 18 }}>Checking&hellip;</div>
            )}
            {v && v.fired.some((f) => f.weight > 0) && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ fontWeight: 700, fontSize: 17 }}>What didn&rsquo;t add up</div>
                {v.fired.filter((f) => f.weight > 0).map((f, i) => (
                  <div key={f.rule} style={{ display: "flex", gap: 12, fontSize: 18, lineHeight: 1.4 }}>
                    <span style={{ flexShrink: 0, width: 28, height: 28, borderRadius: "50%", background: "var(--danger)", color: "#fff", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>{i + 1}</span>
                    <span>{f.reason} <span style={{ color: "var(--muted)", fontSize: 13 }}>· {f.rule}</span></span>
                  </div>
                ))}
              </div>
            )}
            {c.memory && c.memory.hits.length > 0 && (
              <div className="card" style={{ display: "flex", flexDirection: "column", gap: 6, borderColor: "#C9D3F5" }}>
                <div style={{ fontWeight: 700, fontSize: 15 }}>Guardian remembers</div>
                {c.memory.hits.slice(0, 2).map((h, i) => (
                  <div key={i} style={{ fontSize: 15, lineHeight: 1.4 }}><span style={{ color: "var(--muted)", fontSize: 13, marginRight: 8 }}>{h.when}</span>{h.text}</div>
                ))}
                <div style={{ fontSize: 12, color: "var(--muted)" }}>SurrealDB Agent Memory · trace {c.memory.trace_id || "—"}</div>
              </div>
            )}
            {c.money && (
              <div className="card" style={{ borderColor: "var(--gold)", borderWidth: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div className="serif" style={{ fontSize: 34 }}>${c.money.amount.toLocaleString()}</div>
                  <div style={{ color: "var(--muted)", fontSize: 14 }}>by {c.money.method}</div>
                </div>
                <div style={{ fontWeight: 700, fontSize: 18, textAlign: "right", color: c.money.state === "declined" ? "var(--danger)" : c.money.state === "approved" ? "var(--ok)" : "var(--gold)" }}>
                  {c.money.state === "locked" ? `Locked. Waiting for ${c.money.guardian}'s key` : c.money.state === "declined" ? "Stopped by Daniel" : "Approved by Daniel"}
                  {c.money.state === "locked" && <div style={{ fontSize: 13, fontWeight: 500, color: "var(--muted)" }}>Guardian cannot approve. No timeout.</div>}
                </div>
              </div>
            )}
          </section>

          {/* right: the evidence */}
          <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {c.liveView && !d && <iframe src={c.liveView} style={{ width: "100%", height: 380, border: "3px solid #C3CBE0", borderRadius: 24 }} title="Anchor live view" />}
            {d && (
              <div className="card" style={{ padding: 0, overflow: "hidden", borderRadius: 24, border: "3px solid #C3CBE0" }}>
                <div style={{ background: "#F1F2F5", padding: "10px 16px", color: "#8C1D18", fontSize: 14, fontWeight: 600 }}>{String(d.final_domain || "")}</div>
                {d.screenshot_url ? (
                  <img src={`${API}${d.screenshot_url}`} alt="What the link opened, seen from inside the sandbox" style={{ width: "100%", display: "block" }} />
                ) : (
                  <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ fontWeight: 700 }}>{String(d.title || "")}</div>
                    {Array.isArray(d.form_fields) && d.form_fields.length > 0 && (
                      <div style={{ fontSize: 15 }}>The page asks for: {d.form_fields.join(" · ")}</div>
                    )}
                  </div>
                )}
                <div style={{ padding: "10px 16px", fontSize: 13, color: "var(--muted)", borderTop: "1px solid var(--line)" }}>
                  {d.mode === "quarantine" ? `${d.browser === "http" ? "Fetched without a browser" : "Opened with Anchor Browser"}, parsed inside Daytona sandbox ${String(d.sandbox_id || "").slice(0, 8)}` : d.mode === "local" ? "Opened with Anchor Browser" : `Opened in Daytona sandbox ${String(d.sandbox_id || "").slice(0, 8)} with Anchor Browser`}
                  {" · "}{d.redirects?.length || 0} redirects · domain {d.domain_age_days ?? "?"} days old
                  {d.sandbox_destroyed_s != null ? ` · sandbox destroyed in ${d.sandbox_destroyed_s}s` : ""}
                </div>
              </div>
            )}
            {callOrder.filter((k) => c.calls[k]).map((k) => {
              const call = c.calls[k];
              const live = !["completed", "no_answer", "failed"].includes(call.status);
              return (
                <div key={k} className="card" style={{ background: "var(--ink)", color: "#fff", border: "none" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "#B9C0DA", fontSize: 14, marginBottom: 8 }}>
                    <span>{CALL_TITLE[k](c)}</span>
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {live && <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#9EB0FF", animation: "pulse 1s infinite" }} />}
                      {call.status.replace("_", " ")}
                    </span>
                  </div>
                  {call.lines.length === 0 && live && <div className="serif" style={{ fontSize: 19, color: "#7D86A8" }}>{call.status === "dialing" || call.status === "placed" ? "Ringing…" : "On the line. Captions arrive when the call ends."}</div>}
                  {call.lines.slice(-4).map((l, i) => (
                    <div key={i} className="serif" style={{ fontSize: 19, lineHeight: 1.35, color: l.role === "user" ? "#9EB0FF" : "#fff", marginTop: 6 }}>{l.text}</div>
                  ))}
                </div>
              );
            })}
            {c.help && (
              <div className="card" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ fontWeight: 700 }}>Help note for {c.protected}&rsquo;s friends · &ldquo;{c.help.title}&rdquo;</div>
                {c.help.steps.map((s, i) => <div key={i} style={{ fontSize: 15 }}>{i + 1}. {s}</div>)}
                {c.help.audio_url && <audio controls preload="none" src={`${API}${c.help.audio_url}`} style={{ width: "100%", marginTop: 6 }} />}
              </div>
            )}
          </section>
        </div>
      )}

      {/* footer rail */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, borderTop: "1px solid var(--line)", paddingTop: 14 }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          {rail.map((s, i) => (
            <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="pill" style={{ background: s.state === "done" ? "#DDF3EA" : s.state === "active" ? "#E3E8FF" : "#E9ECF3", color: s.state === "todo" ? "var(--muted)" : "var(--ink)" }}>
                {s.state === "done" ? "✓ " : s.state === "active" ? "● " : ""}{s.name}{s.note ? ` · ${s.note}` : ""}
              </span>
              {i < rail.length - 1 && <span style={{ color: "var(--line)" }}>—</span>}
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
          {c?.evals && Object.entries(c.evals).map(([k, ok]) => (
            <span key={k} className="pill" style={{ background: ok ? "#DDF3EA" : "#FCE4E2" }}>Arize · {k.replace("_", " ")} {ok ? "✓" : "✗"}</span>
          ))}
          {c?.timeToCall != null && <span className="pill" style={{ background: "#E4E8F1" }}>first call in {c.timeToCall}s</span>}
          {texts && texts.budget != null && <span className="pill" style={{ background: "#F3F4F8", color: "var(--muted)" }}>texts {texts.sent}/{texts.budget}</span>}
        </div>
      </div>
      <style>{`@keyframes pulse { 0%,100% { opacity: .3 } 50% { opacity: 1 } }`}</style>
    </main>
  );
}
