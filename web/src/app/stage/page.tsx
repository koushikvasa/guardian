"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Mark } from "@/components/Mark";
import { Desk, mainCall } from "@/components/Desk";
import { PhoneAmma } from "@/components/PhoneAmma";
import { PhoneDaniel } from "@/components/PhoneDaniel";
import { API, Beat, CaseState, fireDemo, GEvent, Lang, LANG_NAME, useGuardian, useHealth } from "@/lib/guardian";

const PROTECTED: Record<Lang, string> = { en: "Jasmine", te: "Amma", es: "Rosa" };
const PHRASE: Record<Lang, string> = { en: "Buckie the dog", te: "Kanna", es: "flan de la abuela" };
const BEATS: { key: Beat; hot: string; label: string }[] = [
  { key: "link", hot: "1", label: "bank link" }, { key: "family", hot: "2", label: "“it’s Daniel”" }, { key: "money", hot: "3", label: "$2,000 wire" }, { key: "support", hot: "4", label: "“Microsoft” call" },
];
const SPONSORS = ["Twilio", "Anchor", "Daytona", "SurrealDB", "ElevenLabs", "Arize", "AWS"];

function needsDaniel(c: CaseState | undefined) { return !!c && (!!c.money || !!c.calls.verify || !!c.calls.second_key); }

function lit(c: CaseState | undefined, health: { live?: Record<string, boolean> } | null): Set<string> {
  const s = new Set<string>();
  if (!c) return s;
  s.add("Twilio");
  if (c.detonation) { s.add("Daytona"); if (c.detonation.browser !== "http") s.add("Anchor"); }
  if (c.memory && c.memory.tier && c.memory.tier !== "mock" && c.memory.tier !== "timeout") s.add("SurrealDB");
  if (Object.keys(c.calls).length) s.add("ElevenLabs");
  if (c.evals) s.add("Arize");
  if (health?.live?.bedrock) s.add("AWS");
  return s;
}

/** The one-screen stage: Amma's phone · Guardian's desk · Daniel's phone (only when Daniel is needed). */
export default function Stage() {
  const g = useGuardian();
  const health = useHealth();
  const [lang, setLang] = useState<Lang>("en");
  const [sel, setSel] = useState<string | null>(null);
  const [dry, setDry] = useState(true);  // rehearsal by default: live beats cost texts and calls, so they are a deliberate switch
  const [texts, setTexts] = useState<{ sent: number; budget: number | null } | null>(null);
  const c = (sel && g.cases[sel]) || g.latest;
  const who = c?.protected || PROTECTED[lang];
  const stage = useRef<HTMLDivElement>(null), pA = useRef<HTMLDivElement>(null), pD = useRef<HTMLDivElement>(null), desk = useRef<HTMLDivElement>(null), fly = useRef<HTMLDivElement>(null);
  const showD = needsDaniel(c);

  useEffect(() => { try { setDry(localStorage.getItem("guardian.dry") !== "0"); } catch {} }, []);
  const toggleDry = () => { setDry((d) => { try { localStorage.setItem("guardian.dry", d ? "0" : "1"); } catch {} return !d; }); };
  useEffect(() => { setSel(null); }, [g.order.length]);
  useEffect(() => {
    const tick = () => fetch(`${API}/health`).then((r) => r.json()).then((h) => setTexts(h.texts)).catch(() => {});
    tick(); const id = setInterval(tick, 8000); return () => clearInterval(id);
  }, []);
  const fire = useCallback((b: Beat) => fireDemo(b, lang, dry), [lang, dry]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      const beat = BEATS.find((b) => b.hot === e.key); if (beat) fire(beat.key);
      if (e.key.toLowerCase() === "l") setLang((l) => (l === "en" ? "te" : l === "te" ? "es" : "en"));
      if (e.key.toLowerCase() === "r") toggleDry();
    };
    window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey);
  }, [fire]);

  // flying bubbles: case opened (Amma -> desk), texts out (desk -> phone)
  const flown = useRef(0);
  const flyTo = useCallback((from: HTMLElement | null, to: HTMLElement | null, text: string, inbound: boolean) => {
    const f = fly.current, s = stage.current; if (!f || !s || !from || !to) return;
    const sr = s.getBoundingClientRect(), a = from.getBoundingClientRect(), b = to.getBoundingClientRect();
    f.className = `fly${inbound ? " in" : ""}`; f.textContent = text.slice(0, 90);
    f.style.left = `${a.left - sr.left + a.width * 0.3}px`; f.style.top = `${a.top - sr.top + a.height * 0.25}px`; f.style.opacity = "1"; f.style.transform = "scale(1)";
    requestAnimationFrame(() => requestAnimationFrame(() => { f.style.left = `${b.left - sr.left + b.width * 0.2}px`; f.style.top = `${b.top - sr.top + b.height * 0.35}px`; f.style.transform = "scale(.7)"; }));
    setTimeout(() => { f.style.opacity = "0"; }, 800);
  }, []);
  useEffect(() => {
    const evs = g.sms.slice(flown.current); flown.current = g.sms.length;
    evs.forEach((ev: GEvent) => {
      if (ev.kind !== "sms.out" || !ev.case) return;
      const toD = ev.role === "guardian";
      setTimeout(() => flyTo(desk.current, toD ? pD.current : pA.current, String(ev.body ?? "").replace(/^Guardian: /, ""), false), toD ? 300 : 0);
    });
  }, [g.sms, flyTo]);
  const openedFor = useRef<string | null>(null);
  useEffect(() => {
    if (c && c.text && openedFor.current !== c.id) { openedFor.current = c.id; flyTo(pA.current, desk.current, c.text, true); }
  }, [c, flyTo]);

  const lookAt = useMemo(() => {
    if (!c) return null;
    const mc = mainCall(c); const live = mc && !["completed", "no_answer", "failed"].includes(mc.call.status);
    if (live) return mc.key === "warning" ? { x: -1, y: -0.2 } : { x: 1, y: -0.3 };
    if (c.money?.state === "locked") return { x: 1, y: -0.2 };
    if (!c.verdict) return { x: -1, y: 0.3 };
    return null;
  }, [c]);
  const sponsors = lit(c, health);

  return (
    <main ref={stage} style={{ minHeight: "100vh", padding: "18px 26px 14px", display: "grid", gridTemplateColumns: showD ? "300px 1fr 300px" : "300px 1fr", gridTemplateRows: "auto 1fr auto", gap: "14px 26px", position: "relative", overflow: "hidden", transition: "grid-template-columns .4s" }}>
      {/* top bar */}
      <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700, fontSize: 18 }}><Mark size={40} tilt={false} /> Guardian</div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span className="pill" style={{ background: "#E4E8F1" }}>Today</span>
          {g.order.slice(-5).reverse().map((id) => {
            const x = g.cases[id]; const on = c?.id === id;
            return <button key={id} className="pill" onClick={() => setSel(id)} style={{ cursor: "pointer", border: "1px solid var(--line)", background: on ? "var(--ink)" : "#fff", color: on ? "#fff" : "var(--ink)" }}>{id} · {x.protected || "?"}{x.verdict ? ` · ${x.verdict.label}` : ""}</button>;
          })}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          {(["en", "te", "es"] as Lang[]).map((l) => (
            <button key={l} className="pill" onClick={() => setLang(l)} style={{ cursor: "pointer", border: "1px solid var(--line)", background: lang === l ? "var(--ink)" : "#fff", color: lang === l ? "#fff" : "var(--ink)" }}>{PROTECTED[l]} · {LANG_NAME[l]}</button>
          ))}
          <span style={{ width: 6 }} />
          {BEATS.map((b) => <button key={b.key} className="pill" onClick={() => fire(b.key)} style={{ cursor: "pointer", border: "1px solid var(--line)", background: "#fff" }}><b style={{ color: "var(--accent)" }}>{b.hot}</b> {b.label}</button>)}
          {health?.demo_live ? (
            <button className="pill" onClick={toggleDry} title="R: rehearsal, no texts or calls" style={{ cursor: "pointer", border: "1px solid var(--line)", background: dry ? "#fff" : "#FCE4E2", color: dry ? "var(--muted)" : "#8C1D18", fontWeight: 700 }}>{dry ? "rehearsal · no texts or calls" : "LIVE · texts and calls"}</button>
          ) : (
            <span className="pill" title="The backend has DEMO_LIVE=0: every beat is a rehearsal" style={{ background: "#fff", border: "1px solid var(--line)", color: "var(--muted)" }}>rehearsal only · no texts or calls</span>
          )}
          <span className="pill" style={{ background: g.connected ? "#DDF3EA" : "#FCE4E2", color: g.connected ? "var(--ok)" : "#8C1D18" }}>{g.connected ? "live" : "reconnecting"}</span>
        </div>
      </div>

      {/* Amma */}
      <div style={{ display: "flex", justifyContent: "center", alignItems: "flex-start" }}>
        <PhoneAmma ref={pA} c={c} sms={g.sms} who={who} phrase={PHRASE[(c?.lang as Lang) || lang]} />
      </div>

      {/* desk */}
      <div ref={desk} style={{ minWidth: 0 }}>
        {c ? (
          <Desk c={c} who={who} lookAt={lookAt} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 760 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}><Mark size={96} mood="idle" /><div className="serif" style={{ fontSize: 26 }}>Watching. Nothing to do.</div></div>
            <h1 className="serif" style={{ fontSize: 48, lineHeight: 1.06, margin: 0 }}>{PROTECTED[lang]} doesn&rsquo;t forward anything. Her phone does, and her family answers.</h1>
            <p style={{ fontSize: 19, color: "var(--muted)", margin: 0, lineHeight: 1.45 }}>Text {PROTECTED[lang]}&rsquo;s phone from any number, or press <b>1</b>–<b>4</b> to fire a beat in {LANG_NAME[lang]}. <b>L</b> switches the family member, <b>R</b> toggles rehearsal.</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {(["te", "en", "es"] as Lang[]).map((l) => <span key={l} className="pill" style={{ background: "#fff", border: "1px solid var(--line)" }}>{PROTECTED[l]} · {LANG_NAME[l]} · “{PHRASE[l]}”</span>)}
              <span className="pill" style={{ background: "#fff", border: "1px solid var(--line)" }}>Daniel · guardian · holds the second key</span>
            </div>
          </div>
        )}
      </div>

      {/* Daniel: only when needed */}
      {showD && (
        <div className="col" style={{ display: "flex", justifyContent: "center", alignItems: "flex-start" }}>
          <PhoneDaniel ref={pD} c={c} sms={g.sms} />
        </div>
      )}

      {/* rail */}
      <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, borderTop: "1px solid var(--line)", paddingTop: 10, flexWrap: "wrap" }}>
        <div className="sp" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {SPONSORS.map((s) => <span key={s} className={`pill${sponsors.has(s) ? " lit" : ""}`} style={{ background: sponsors.has(s) ? undefined : "#F3F4F8" }}>{s}</span>)}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          {c?.timeToCall != null && <span className="pill" style={{ background: "#E4E8F1" }}>first call in {c.timeToCall}s</span>}
          {texts && texts.budget != null && <span className="pill" style={{ background: "#F3F4F8", color: "var(--muted)" }}>texts {texts.sent}/{texts.budget}</span>}
        </div>
      </div>
      <div ref={fly} className="fly" aria-hidden="true" />
    </main>
  );
}
