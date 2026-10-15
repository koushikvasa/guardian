"use client";
import Link from "next/link";
import { Brand, Mark } from "@/components/Mark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Hero } from "@/components/Hero";
import { CaseState, useHealth } from "@/lib/guardian";

/** Sample case states so the hero objects on the landing page show their finished beat. */
const LINK: CaseState = { id: "L", status: "closed", calls: {}, text: "https://keystone-verifica.top/login", protected: "Amma", lang: "te", detonation: { final_domain: "keystone-verifica.top", sandbox_destroyed_s: 0.05, form_fields: ["Password", "Card number"] } };
const MONEY: CaseState = { id: "M", status: "closed", calls: {}, protected: "Amma", lang: "te", money: { amount: 2000, method: "wire", state: "declined", guardian: "Daniel" } };
const FAMILY: CaseState = { id: "F", status: "closed", calls: { verify: { status: "completed", lines: [] } }, protected: "Amma", lang: "te", sender: "a number ending 0199", verify: "denied", text: "it's me Daniel" };

const PRODUCTS = [
  { title: "Safe link opening", c: LINK, body: "Guardian opens the link so she never has to. A cloud browser follows it, the page is parsed inside a throwaway Daytona sandbox with no network, and the sandbox is destroyed. She hears what was wrong, in her language." },
  { title: "Verify by callback", c: FAMILY, body: "Someone texts “it’s me, Daniel, I need help.” Guardian doesn’t guess. It calls the real Daniel on the number the family saved and asks one question. The scammer controls the number that texted her, not the one Guardian calls back." },
  { title: "The money second key", c: MONEY, body: "Any money request above the family’s limit is locked until a second family member turns the key: a press-and-hold on Daniel’s own phone. Guardian never approves, a spoken yes never approves, and there is no timeout." },
];
const STEPS = ["Received", "Opened in a sandbox", "Verdict, by rules", "Call, in her language", "Teach-back", "Help note for her friends", "Remembered"];
const SPONSORS: [string, string][] = [
  ["ElevenLabs + Twilio", "Four voice agents (Telugu, English, Spanish warning calls; the callback; the second-key call) and the family’s phone line."],
  ["Daytona", "Every link is parsed inside a fresh sandbox from a prebuilt snapshot, then destroyed. The page never touches a family device."],
  ["Anchor", "The cloud browser that follows the link, its redirects and its screenshot, away from everyone’s phone."],
  ["SurrealDB Agent Memory", "Guardian remembers verdicts as typed facts. The next time the same link, sender or story appears, it already knows, with a retrieval trace."],
  ["Arize", "Every case is a trace. Three live checks on each: every reason cites a rule, nothing Guardian says asks for a secret, the language matches. Offline experiments score the rules on a labelled set."],
  ["AWS Bedrock", "Extracts signals from the message. The model only reads; deterministic rules decide."],
];

/** The pitch in one screen, for whoever opens the project link before the demo. */
export default function Home() {
  const health = useHealth();
  const live = Object.values(health?.live || {}).filter(Boolean).length;
  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 24px 72px", display: "flex", flexDirection: "column", gap: 44 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <Brand size={60} />
        <div style={{ display: "flex", gap: 8 }}>
          <ThemeToggle />
          <Link href="/family" className="pill" style={{ background: "var(--card)", border: "1px solid var(--line)", textDecoration: "none", color: "inherit" }}>Family</Link>
          <Link href="/stage" className="pill" style={{ background: "var(--dark)", color: "#fff", textDecoration: "none" }}>Open the stage</Link>
        </div>
      </div>

      <section style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 32, alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <h1 className="serif" style={{ fontSize: 58, lineHeight: 1.05, margin: 0, textWrap: "balance" }}>Amma doesn&rsquo;t forward anything. Her phone does, and her family answers.</h1>
          <p style={{ fontSize: 20, color: "var(--muted)", lineHeight: 1.5, margin: 0, maxWidth: 560 }}>An AI scam shield for families. Guardian reads what a stranger sends, opens links where they can&rsquo;t hurt anyone, calls the real relative before anyone sends money, and explains it all to her in her own language: Telugu, English or Spanish.</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link href="/stage" className="btn btn-dark" style={{ display: "inline-flex", alignItems: "center", textDecoration: "none" }}>See it run</Link>
            <Link href="/family" className="btn btn-ghost" style={{ display: "inline-flex", alignItems: "center", textDecoration: "none" }}>How a family sets it up</Link>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}><Mark size={260} title="Guardian, always looking" /></div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 18 }}>
        {PRODUCTS.map((p) => (
          <div key={p.title} className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}><Hero c={p.c} /></div>
            <h2 className="serif" style={{ fontSize: 26, margin: 0 }}>{p.title}</h2>
            <p style={{ fontSize: 16, lineHeight: 1.5, color: "var(--muted)" }}>{p.body}</p>
          </div>
        ))}
      </section>

      <section className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <h2 className="serif" style={{ fontSize: 28, margin: 0 }}>Every case runs the same seven steps.</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {STEPS.map((s, i) => <span key={s} style={{ display: "flex", alignItems: "center", gap: 8 }}><span className="pill" style={{ background: "var(--chip)" }}>{s}</span>{i < STEPS.length - 1 && <span style={{ color: "var(--line)" }}>—</span>}</span>)}
        </div>
        <p style={{ fontSize: 16, color: "var(--muted)", lineHeight: 1.5 }}>Rules decide, not the model. Every reason she hears cites the rule that fired. Guardian never asks for codes, passwords, cards or payments, and a live check on every case proves it. The fourth kind of scam, the “Microsoft” support call, runs the same way from what she tells Guardian in her own words.</p>
      </section>

      <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 8 }}>
          <h2 className="serif" style={{ fontSize: 28, margin: 0 }}>Built on the sponsors, each doing a real job.</h2>
          {health && <span className="pill" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>{live} of {Object.keys(health.live || {}).length} live right now</span>}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 12 }}>
          {SPONSORS.map(([n, b]) => <div key={n} className="card" style={{ padding: "14px 16px" }}><div style={{ fontWeight: 700, marginBottom: 4 }}>{n}</div><div style={{ fontSize: 15, color: "var(--muted)", lineHeight: 1.45 }}>{b}</div></div>)}
        </div>
      </section>

      <footer style={{ color: "var(--muted)", fontSize: 14 }}>Daytona HackSprint NYC, October 2026. Demo family: Amma (Telugu), Jasmine (English), Rosa (Spanish), and Daniel, who holds the second key.</footer>
    </main>
  );
}
