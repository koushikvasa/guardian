"use client";
import { useEffect, useState } from "react";

type T = "light" | "dark" | "system";
const NEXT: Record<T, T> = { system: "dark", dark: "light", light: "system" };

/** Light / dark / system. Stored per browser; applied before first paint by the inline script in layout.tsx. */
export function ThemeToggle() {
  const [t, setT] = useState<T>("system");
  useEffect(() => { try { setT((localStorage.getItem("guardian.theme") as T) || "system"); } catch {} }, []);
  const apply = (v: T) => {
    setT(v);
    try { localStorage.setItem("guardian.theme", v); } catch {}
    const root = document.documentElement;
    if (v === "system") root.removeAttribute("data-theme"); else root.setAttribute("data-theme", v);
  };
  const label = t === "dark" ? "Dark" : t === "light" ? "Light" : "Auto";
  return (
    <button onClick={() => apply(NEXT[t])} className="pill" title="Theme: light / dark / system" aria-label={`Theme: ${label}`} style={{ cursor: "pointer", border: "1px solid var(--line)", background: "var(--card)", color: "var(--fg)" }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
        {t === "dark" ? <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /> : <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>}
      </svg>
      {label}
    </button>
  );
}
