"use client";
import { useEffect, useRef, useState } from "react";
import { API } from "@/lib/guardian";

/** Demo / Live for the whole backend. Going live takes two clicks within three seconds, so it never happens by accident. */
export function ModeSwitch({ mode, onChange }: { mode: "demo" | "live" | null; onChange?: (m: "demo" | "live") => void }) {
  const [arm, setArm] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const set = async (m: "demo" | "live") => {
    await fetch(`${API}/mode`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ mode: m }) }).catch(() => {});
    onChange?.(m);
  };
  const click = () => {
    if (mode === "live") { set("demo"); setArm(false); return; }
    if (!arm) { setArm(true); timer.current = setTimeout(() => setArm(false), 3000); return; }
    setArm(false); set("live");
  };
  const live = mode === "live";
  return (
    <button onClick={click} className="pill" title="R: demo / live" aria-pressed={live}
      style={{ cursor: "pointer", border: `1px solid ${live ? "var(--danger)" : "var(--line)"}`, background: live ? "var(--danger)" : arm ? "var(--warn-soft)" : "var(--card)", color: live ? "#fff" : arm ? "var(--gold-text)" : "var(--fg)", fontWeight: 700, minWidth: 92, justifyContent: "center" }}>
      {live ? "● LIVE" : arm ? "click again to go live" : "DEMO"}
    </button>
  );
}
