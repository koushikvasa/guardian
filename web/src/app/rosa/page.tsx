"use client";
import { Logo } from "@/components/Logo";
import { useGuardian } from "@/lib/guardian";

const UI: Record<string, { calling: string; empty: string }> = {
  en: { calling: "Call in progress", empty: "No messages yet." },
  te: { calling: "కాల్ జరుగుతోంది", empty: "ఇంకా మెసేజ్‌లు లేవు." },
  es: { calling: "Llamada en curso", empty: "Sin mensajes todavía." },
};

/** The protected member's phone (Amma / Jasmine / Rosa): her SMS thread with Guardian, and captions while Guardian calls her. */
export default function Rosa() {
  const { sms: all, latest } = useGuardian();
  const sms = all.filter((m) => m.role !== "guardian"); // Daniel's texts go to his phone, not hers
  const call = latest?.calls?.warning;
  const lang = latest?.lang || "en";
  const ui = UI[lang] || UI.en;
  const onCall = call && call.status !== "completed" && call.status !== "no_answer" && call.status !== "failed";

  if (onCall) {
    return (
      <main className="phone" lang={lang} style={{ background: "var(--ink)", color: "#fff" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 52, height: 52, borderRadius: "50%", background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Logo size={38} color="#fff" bg="var(--accent)" />
          </div>
          <div><div style={{ fontWeight: 700, fontSize: 20 }}>Guardian</div><div style={{ color: "#B9C0DA" }}>{ui.calling}</div></div>
        </div>
        <div style={{ marginTop: 30, display: "flex", flexDirection: "column", gap: 18 }}>
          {call.lines.map((l, i) => (
            <div key={i} className="serif" style={{ fontSize: i === call.lines.length - 1 ? 30 : 22, lineHeight: 1.25, color: i === call.lines.length - 1 ? "#fff" : l.role === "user" ? "#9EB0FF" : "#7D86A8" }}>{l.text}</div>
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="phone" lang={lang}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, paddingBottom: 14, borderBottom: "1px solid var(--line)" }}>
        <Logo size={40} />
        <div style={{ fontWeight: 700, fontSize: 18 }}>Guardian</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 16 }}>
        {sms.length === 0 && <div style={{ color: "var(--muted)" }}>{ui.empty}</div>}
        {sms.map((m, i) => {
          const mine = m.kind === "sms.in";
          return (
            <div key={i} style={{ alignSelf: mine ? "flex-end" : "flex-start", maxWidth: "82%", background: mine ? "var(--accent)" : "#fff", color: mine ? "#fff" : "var(--ink)", border: mine ? "none" : "1px solid var(--line)", borderRadius: 18, padding: "10px 14px", fontSize: 17, lineHeight: 1.35 }}>
              {String(m.body ?? "").replace(/^Guardian: /, "")}
            </div>
          );
        })}
      </div>
    </main>
  );
}
