export function Logo({ size = 48, color = "var(--accent)", bg = "var(--bg)" }: { size?: number; color?: string; bg?: string }) {
  return (
    <svg width={size} height={(size * 20) / 37} viewBox="6 14 37 20" aria-hidden="true">
      <rect x="7.5" y="16" width="34" height="16" rx="8" fill={color} />
      <path d="M15.59 19.5 H21.91 A5.5 5.5 0 0 1 21.91 28.5 H15.59 A5.5 5.5 0 0 1 15.59 19.5 Z" fill={bg} />
      <path d="M27.09 19.5 H33.41 A5.5 5.5 0 0 1 33.41 28.5 H27.09 A5.5 5.5 0 0 1 27.09 19.5 Z" fill={bg} />
      <circle cx="21.05" cy="23" r="2.3" fill={color} />
      <circle cx="32.55" cy="23" r="2.3" fill={color} />
    </svg>
  );
}

export function Brand({ size = 48 }: { size?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <Logo size={size} />
      <span style={{ fontWeight: 700, fontSize: size * 0.42 }}>Guardian</span>
    </div>
  );
}
