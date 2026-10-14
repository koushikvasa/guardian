"use client";
import { Brand } from "@/components/Logo";
import { API, useGuardian } from "@/lib/guardian";

const LABEL: Record<string, { text: string; color: string; bg: string }> = {
  scam: { text: "Scam", color: "#fff", bg: "var(--danger)" },
  suspicious: { text: "Suspicious", color: "#6B4A10", bg: "#FFF3D6" },
  safe: { text: "Safe", color: "#fff", bg: "var(--ok)" },
};

/** Generic live stage view. Thursday: split into /stage/callback, /stage/keys, /stage/jar per the hero designs. */
export default function Stage() {
  const { latest: c, connected } = useGuardian();
  const v = c?.verdict;
  const d = c?.detonation;
  const callOrder = ["verify", "second_key", "warning"];
  return (
    <main style={{ minHeight: "100vh", padding: "40px 64px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48 }}>
      <section style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Brand />
          <span className="pill" style={{ background: connected ? "#DDF3EA" : "#FCE4E2" }}>{connected ? "live" : "reconnecting"}</span>
        </div>
        {!c && <h1 className="serif" style={{ fontSize: 56 }}>Waiting for Rosa&rsquo;s phone&hellip;</h1>}
        {c && (
          <>
            <div style={{ color: "var(--muted)", fontWeight: 600 }}>Case {c.id}</div>
            <div className="card" style={{ borderRadius: "4px 18px 18px 18px", fontSize: 20 }} lang={c.lang}>{c.text}</div>
            {v && (
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <span className="pill" style={{ fontSize: 22, padding: "8px 18px", background: LABEL[v.label].bg, color: LABEL[v.label].color }}>{LABEL[v.label].text}</span>
                <span style={{ color: "var(--muted)", fontSize: 18 }}>score {v.score}</span>
              </div>
            )}
            {v && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ fontWeight: 700, fontSize: 18 }}>What didn&rsquo;t add up</div>
                {v.fired.filter((f) => f.weight > 0).map((f, i) => (
                  <div key={f.rule} style={{ display: "flex", gap: 12, fontSize: 18, lineHeight: 1.4 }}>
                    <span style={{ flexShrink: 0, width: 30, height: 30, borderRadius: "50%", background: "var(--danger)", color: "#fff", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</span>
                    <span>{f.reason} <span style={{ color: "var(--muted)", fontSize: 14 }}>· {f.rule}</span></span>
                  </div>
                ))}
              </div>
            )}
            {c.money && (
              <div className="card" style={{ borderColor: "var(--gold)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="serif" style={{ fontSize: 30 }}>${c.money.amount.toLocaleString()}</div>
                <div style={{ fontWeight: 700, color: c.money.state === "declined" ? "var(--danger)" : c.money.state === "approved" ? "var(--ok)" : "var(--gold)" }}>
                  {c.money.state === "locked" ? `Waiting for ${c.money.guardian}'s key` : c.money.state === "declined" ? "Stopped by Daniel" : "Approved by Daniel"}
                </div>
              </div>
            )}
            {c.evals && (
              <div style={{ display: "flex", gap: 8 }}>
                {Object.entries(c.evals).map(([k, ok]) => (
                  <span key={k} className="pill" style={{ background: ok ? "#DDF3EA" : "#FCE4E2" }}>Arize · {k} {ok ? "✓" : "✗"}</span>
                ))}
                {c.timeToCall != null && <span className="pill" style={{ background: "#E4E8F1" }}>first call in {c.timeToCall}s</span>}
              </div>
            )}
          </>
        )}
      </section>

      <section style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {c?.liveView && !d && <iframe src={c.liveView} style={{ width: "100%", height: 420, border: "3px solid #C3CBE0", borderRadius: 24 }} title="Anchor live view" />}
        {d && (
          <div className="card" style={{ padding: 0, overflow: "hidden", borderRadius: 28, border: "3px solid #C3CBE0" }}>
            <div style={{ background: "#F1F2F5", padding: "10px 16px", color: "#8C1D18", fontSize: 14 }}>{String(d.final_domain || "")}</div>
            {d.screenshot_url && <img src={`${API}${d.screenshot_url}`} alt="What the link opened, seen from inside the sandbox" style={{ width: "100%", display: "block" }} />}
            <div style={{ padding: "12px 16px", fontSize: 14, color: "var(--muted)" }}>
              Opened in Daytona sandbox {String(d.sandbox_id || "")} with Anchor Browser · {d.redirects?.length || 0} redirects · domain {d.domain_age_days ?? "?"} days old · sandbox destroyed in {d.sandbox_destroyed_s ?? "?"}s
            </div>
          </div>
        )}
        {c && callOrder.filter((k) => c.calls[k]).map((k) => (
          <div key={k} className="card" style={{ background: "var(--ink)", color: "#fff", border: "none" }}>
            <div style={{ display: "flex", justifyContent: "space-between", color: "#B9C0DA", fontSize: 14, marginBottom: 8 }}>
              <span>{k === "verify" ? "Calling the real Daniel" : k === "second_key" ? "Second key call to Daniel" : "Warning call to Rosa"}</span>
              <span>{c.calls[k].status}</span>
            </div>
            {c.calls[k].lines.slice(-4).map((l, i) => (
              <div key={i} className="serif" style={{ fontSize: 19, lineHeight: 1.35, color: l.role === "user" ? "#9EB0FF" : "#fff", marginTop: 6 }}>{l.text}</div>
            ))}
          </div>
        ))}
      </section>
    </main>
  );
}
