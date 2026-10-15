"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Mark } from "@/components/Mark";
import { API, CaseState, LANG_NAME, useGuardian } from "@/lib/guardian";

const PROTECTED_NAME: Record<string, string> = { jasmine: "Jasmine", amma: "Amma", rosa: "Rosa" };

type Member = { id: string; name: string; role: string; lang: string; safe_phrase?: string | null; phone: string; whatsapp?: string | null; story_facts: string[] };
type Family = { name: string; second_key_threshold_usd: number; members: Member[] };
type Hit = { text: string; when: string; score: number };

/** The family page: who is protected, their phrases and languages, the money threshold, today's cases, and what Guardian remembers. */
export default function FamilyPage() {
  const g = useGuardian();
  const [fam, setFam] = useState<Family | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [q, setQ] = useState("What does Guardian know about Daniel?");
  const [mem, setMem] = useState<{ hits: Hit[]; trace_id?: string | null; tier?: string | null } | null>(null);
  const [asking, setAsking] = useState(false);
  const load = () => fetch(`${API}/family`).then((r) => r.json()).then(setFam).catch(() => setFam(null));
  useEffect(() => { load(); }, []);
  const ask = async (query: string) => { setAsking(true); try { setMem(await (await fetch(`${API}/memory?q=${encodeURIComponent(query)}`)).json()); } catch { setMem(null); } setAsking(false); };
  useEffect(() => { ask(q); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  const patch = async (body: object, key: string) => { setSaving(key); await fetch(`${API}/family`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }); await load(); setSaving(null); };
  const [past, setPast] = useState<CaseState[]>([]);
  useEffect(() => { fetch(`${API}/cases`).then((r) => r.json()).then((cs: CaseState[]) => setPast(cs.map((c) => ({ ...c, protected: PROTECTED_NAME[c.protected || ""] || c.protected, calls: c.calls || {} })))).catch(() => {}); }, [g.order.length]);
  const liveIds = new Set(g.order);
  const cases = [...g.order.slice().reverse().map((id) => g.cases[id]), ...past.filter((c) => !liveIds.has(c.id)).reverse()];
  const protectedM = fam?.members.filter((m) => m.role === "protected") || [];
  const others = fam?.members.filter((m) => m.role !== "protected") || [];

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "36px 24px 64px", display: "flex", flexDirection: "column", gap: 28 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700, fontSize: 20, color: "inherit", textDecoration: "none" }}><Mark size={44} /> Guardian</Link>
        <div style={{ display: "flex", gap: 8 }}>
          <Link href="/stage" className="pill" style={{ background: "var(--ink)", color: "#fff", textDecoration: "none" }}>Open the stage</Link>
          <span className="pill" style={{ background: g.connected ? "#DDF3EA" : "#FCE4E2", color: g.connected ? "var(--ok)" : "#8C1D18" }}>{g.connected ? "live" : "offline"}</span>
        </div>
      </div>

      <div>
        <div style={{ color: "var(--muted)", fontWeight: 600, fontSize: 14, letterSpacing: ".08em", textTransform: "uppercase" }}>Daniel&rsquo;s family</div>
        <h1 className="serif" style={{ fontSize: 44, lineHeight: 1.08, margin: "6px 0 0" }}>{fam?.name || "Your family"}</h1>
        <p style={{ color: "var(--muted)", fontSize: 18, margin: "10px 0 0", maxWidth: 680 }}>Each protected person has her own language and her own family phrase. Guardian says the phrase at the start of every call it makes to her, so she knows it&rsquo;s real. Nobody else ever hears it.</p>
      </div>

      {/* protected members */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
        {protectedM.map((m) => (
          <div key={m.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div className="serif" style={{ fontSize: 30 }}>{m.name}</div>
              <span className="pill" style={{ background: "#E4E8F1" }}>protected · {LANG_NAME[m.lang] || m.lang}</span>
            </div>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>
              Family phrase
              <input id={`phrase-${m.id}`} defaultValue={m.safe_phrase || ""} onBlur={(e) => { if (e.target.value !== (m.safe_phrase || "")) patch({ members: [{ id: m.id, safe_phrase: e.target.value }] }, m.id); }}
                style={{ font: "inherit", fontSize: 18, fontWeight: 600, color: "var(--ink)", padding: "10px 12px", border: "1px solid var(--line)", borderRadius: 12, background: "#fff" }} />
            </label>
            <div style={{ fontSize: 14, color: "var(--muted)" }}>Phone {m.phone}{m.whatsapp ? ` · WhatsApp ${m.whatsapp}` : ""}</div>
            {m.story_facts.length > 0 && <div style={{ fontSize: 14 }}><div style={{ color: "var(--muted)", fontWeight: 600, marginBottom: 4 }}>Things only the family knows</div>{m.story_facts.map((f) => <div key={f}>• {f}</div>)}</div>}
            {saving === m.id && <div style={{ fontSize: 13, color: "var(--ok)" }}>Saved.</div>}
          </div>
        ))}
      </section>

      {/* guardian + threshold */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
        {others.map((m) => (
          <div key={m.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div className="serif" style={{ fontSize: 26 }}>{m.name}</div>
              <span className="pill" style={{ background: m.role === "guardian" ? "#F6E7C5" : "#E4E8F1", color: m.role === "guardian" ? "#6B4A10" : "inherit" }}>{m.role === "guardian" ? "guardian · holds the second key" : "family member"}</span>
            </div>
            <div style={{ fontSize: 14, color: "var(--muted)" }}>{LANG_NAME[m.lang] || m.lang} · phone {m.phone}{m.whatsapp ? ` · WhatsApp ${m.whatsapp}` : ""}</div>
            {m.role === "guardian" && <div style={{ fontSize: 14 }}>Guardian calls {m.name} on this saved number whenever someone claims to be family, and whenever money above the threshold is requested. Only {m.name}&rsquo;s press-and-hold can approve a payment.</div>}
          </div>
        ))}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8, borderColor: "var(--gold)" }}>
          <div style={{ fontWeight: 700 }}>Money needs a second key above</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="serif" style={{ fontSize: 30 }}>$</span>
            <input id="threshold" type="number" min={0} step={50} defaultValue={fam?.second_key_threshold_usd ?? 500} onBlur={(e) => { const v = Number(e.target.value); if (fam && v !== fam.second_key_threshold_usd) patch({ second_key_threshold_usd: v }, "threshold"); }}
              style={{ font: "inherit", fontSize: 28, fontFamily: "'Young Serif', serif", width: 160, padding: "6px 10px", border: "1px solid var(--line)", borderRadius: 12, background: "#fff", color: "var(--ink)" }} />
            {saving === "threshold" && <span style={{ fontSize: 13, color: "var(--ok)" }}>Saved.</span>}
          </div>
          <div style={{ fontSize: 14, color: "var(--muted)" }}>Any request above this is locked until Daniel turns the key. Guardian itself never approves, and there is no timeout.</div>
        </div>
      </section>

      {/* today + memory */}
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
          <div style={{ fontWeight: 700 }}>Today</div>
          {cases.length === 0 && <div style={{ color: "var(--muted)", fontSize: 15 }}>No cases yet. They appear here as they happen.</div>}
          {cases.slice(0, 8).map((c) => (
            <div key={c.id} style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 10, alignItems: "center", fontSize: 15, borderTop: "1px solid var(--line)", paddingTop: 8 }}>
              <span className="pill" style={{ background: c.verdict?.label === "scam" ? "#FCE4E2" : c.verdict?.label === "suspicious" ? "#FFF3D6" : "#DDF3EA", color: c.verdict?.label === "scam" ? "#8C1D18" : c.verdict?.label === "suspicious" ? "#6B4A10" : "var(--ok)" }}>{c.verdict?.label || "checking"}</span>
              <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}><b>{c.protected}</b> · {c.text}</span>
              <span style={{ color: "var(--muted)", fontSize: 13 }}>{c.money ? `$${c.money.amount.toLocaleString()} ${c.money.state}` : c.timeToCall != null ? `call in ${c.timeToCall}s` : ""}</span>
            </div>
          ))}
        </div>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
          <div style={{ fontWeight: 700 }}>What Guardian remembers</div>
          <form onSubmit={(e) => { e.preventDefault(); ask(q); }} style={{ display: "flex", gap: 8 }}>
            <input id="memq" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, font: "inherit", padding: "9px 12px", border: "1px solid var(--line)", borderRadius: 12, background: "#fff", color: "var(--ink)", minWidth: 0 }} />
            <button className="btn btn-dark" type="submit" style={{ minHeight: 42 }}>{asking ? "…" : "Ask"}</button>
          </form>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["What does Guardian know about Daniel?", "Which links were scams?", "Who asked for money?"].map((s) => <button key={s} type="button" className="pill" onClick={() => { setQ(s); ask(s); }} style={{ cursor: "pointer", border: "1px solid var(--line)", background: "#fff" }}>{s}</button>)}
          </div>
          {mem && mem.hits.length === 0 && <div style={{ color: "var(--muted)", fontSize: 15 }}>Nothing yet for that question.</div>}
          {mem?.hits.slice(0, 5).map((h, i) => (
            <div key={i} style={{ fontSize: 15, lineHeight: 1.4, borderTop: "1px solid var(--line)", paddingTop: 8 }}><span style={{ color: "var(--muted)", fontSize: 13, marginRight: 8 }}>{h.when}</span>{h.text}</div>
          ))}
          {mem && <div style={{ fontSize: 12, color: "var(--muted)" }}>SurrealDB Agent Memory · {mem.tier || "mock"}{mem.trace_id ? ` · trace ${mem.trace_id}` : ""}</div>}
        </div>
      </section>
    </main>
  );
}
