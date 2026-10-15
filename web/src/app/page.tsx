"use client";
import Link from "next/link";
import { useState } from "react";
import { Brand } from "@/components/Logo";
import { API, fireDemo, Lang, LANG_NAME, useGuardian, useHealth } from "@/lib/guardian";

const SPONSORS = ["daytona", "anchor", "elevenlabs", "twilio_sms", "surreal_memory", "surrealdb", "bedrock", "arize"];
const PROTECTED: Record<Lang, string> = { en: "Jasmine", te: "Amma", es: "Rosa" };

export default function Home() {
  const g = useGuardian();
  const health = useHealth();
  const [lang, setLang] = useState<Lang>("en");
  return (
    <main style={{ maxWidth: 980, margin: "0 auto", padding: "48px 24px" }}>
      <Brand size={56} />
      <h1 className="serif" style={{ fontSize: 52, lineHeight: 1.08, margin: "28px 0 10px", maxWidth: 760 }}>
        Amma doesn&rsquo;t forward anything. Her phone does, and her family answers.
      </h1>
      <p style={{ fontSize: 19, color: "var(--muted)", maxWidth: 680, lineHeight: 1.5 }}>
        Guardian opens suspicious links in a sealed sandbox, calls the real relative before anyone sends money, and
        explains it all in her own language: Telugu for Amma, English for Jasmine, Spanish for Rosa.
      </p>

      <div style={{ display: "flex", gap: 8, margin: "28px 0 10px", alignItems: "center" }}>
        <span style={{ color: "var(--muted)", fontSize: 14 }}>Demo as</span>
        {(["en", "te", "es"] as Lang[]).map((l) => (
          <button key={l} className="pill" onClick={() => setLang(l)}
            style={{ cursor: "pointer", border: "1px solid var(--line)", background: lang === l ? "var(--ink)" : "#fff", color: lang === l ? "#fff" : "var(--ink)" }}>
            {PROTECTED[l]} · {LANG_NAME[l]}
          </button>
        ))}
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "0 0 28px" }}>
        <button className="btn btn-dark" onClick={() => fireDemo("link", lang)}>Fire demo: bank link</button>
        <button className="btn btn-dark" onClick={() => fireDemo("family", lang)}>Fire demo: &ldquo;It&rsquo;s Daniel&rdquo;</button>
        <button className="btn btn-dark" onClick={() => fireDemo("money", lang)}>Fire demo: $2,000 wire</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
        {[
          ["/stage", "Stage screen", "The live case, for the projector"],
          ["/rosa", "Her phone", "Texts and call captions, in her language"],
          [`/daniel/key/${g.latest?.money ? g.latest.id : "latest"}`, "Daniel’s key", "Approve or stop the money"],
        ].map(([href, title, sub]) => (
          <Link key={href} href={href} className="card" style={{ textDecoration: "none", color: "inherit" }}>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{title}</div>
            <div style={{ color: "var(--muted)", marginTop: 4 }}>{sub}</div>
          </Link>
        ))}
      </div>

      <div className="card" style={{ marginTop: 28 }}>
        <div style={{ fontWeight: 700, marginBottom: 10 }}>
          Backend {g.connected ? <span style={{ color: "var(--ok)" }}>connected</span> : <span style={{ color: "var(--danger)" }}>offline</span>}
          <span style={{ color: "var(--muted)", fontWeight: 400 }}> · {API}</span>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {SPONSORS.map((s) => {
            const live = health?.live?.[s];
            return (
              <span key={s} className="pill" style={{ background: live ? "#DDF3EA" : "#E4E8F1", color: live ? "var(--ok)" : "var(--muted)" }}>
                {s.replace("_sms", "")}: {health ? (live ? "live" : "mock") : "?"}
              </span>
            );
          })}
        </div>
      </div>
    </main>
  );
}
