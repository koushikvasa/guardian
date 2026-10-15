"use client";
import { useEffect, useState } from "react";
import { API } from "@/lib/guardian";

type Node = { id: string; label: string; kind: "member" | "guardian" | "sender" | "domain" | "story" | "brand" | "knowledge"; scam?: boolean; detail?: string; when?: string };
type Edge = { from: string; to: string; label?: string; scam?: boolean };
type G = { nodes: Node[]; edges: Edge[]; trace_id?: string | null; tier?: string | null };

const RING: Record<Node["kind"], number> = { member: 1, guardian: 1, sender: 2, domain: 2, story: 2, brand: 3, knowledge: 3 };
const FILL: Record<Node["kind"], string> = { member: "#2E46E5", guardian: "#B8862B", sender: "#D7322A", domain: "#D7322A", story: "#D7322A", brand: "#4A5170", knowledge: "#4A5170" };

/** What Guardian knows, as a graph: the family in the middle, threats it has seen on the next ring, the scam knowledge it was given on the outer ring. */
export function MemoryGraph({ compact = false }: { compact?: boolean }) {
  const [g, setG] = useState<G | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  useEffect(() => { const load = () => fetch(`${API}/memory/graph`).then((r) => r.json()).then(setG).catch(() => {}); load(); const id = setInterval(load, 20000); return () => clearInterval(id); }, []);
  const W = 760, H = compact ? 420 : 560, cx = W / 2, cy = H / 2;
  const radius = [0, compact ? 70 : 95, compact ? 150 : 200, compact ? 200 : 265];
  const pos = new Map<string, { x: number; y: number }>();
  if (g) {
    [1, 2, 3].forEach((ring) => {
      const ns = g.nodes.filter((n) => RING[n.kind] === ring);
      ns.forEach((n, i) => { const a = -Math.PI / 2 + (i / Math.max(1, ns.length)) * Math.PI * 2 + (ring === 2 ? 0.25 : ring === 3 ? 0.1 : 0); pos.set(n.id, { x: cx + Math.cos(a) * radius[ring], y: cy + Math.sin(a) * radius[ring] }); });
    });
  }
  const near = (id: string) => !hover || hover === id || g?.edges.some((e) => (e.from === hover && e.to === id) || (e.to === hover && e.from === id));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }} role="img" aria-label="What Guardian knows, as a graph">
        {[1, 2, 3].map((r) => <circle key={r} cx={cx} cy={cy} r={radius[r]} fill="none" stroke="var(--line)" strokeDasharray={r === 1 ? undefined : "4 6"} />)}
        <text x={cx} y={cy - radius[1] - 10} textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="Figtree, sans-serif" letterSpacing=".08em">FAMILY</text>
        <text x={cx} y={cy - radius[2] - 10} textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="Figtree, sans-serif" letterSpacing=".08em">SEEN · REMEMBERED</text>
        <text x={cx} y={cy - radius[3] - 10} textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="Figtree, sans-serif" letterSpacing=".08em">SCAM KNOWLEDGE</text>
        {g?.edges.map((e, i) => { const a = pos.get(e.from), b = pos.get(e.to); if (!a || !b) return null; const dim = hover && !(hover === e.from || hover === e.to); return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={e.scam ? "#D7322A" : "#9EB0FF"} strokeWidth={hover && !dim ? 3 : 1.5} strokeDasharray={e.scam ? undefined : "5 5"} opacity={dim ? 0.15 : 0.8} />; })}
        {g?.nodes.map((n) => {
          const p = pos.get(n.id); if (!p) return null;
          const r = n.kind === "member" || n.kind === "guardian" ? 22 : n.kind === "brand" || n.kind === "knowledge" ? 12 : 15;
          const dim = !near(n.id);
          return (
            <g key={n.id} transform={`translate(${p.x} ${p.y})`} opacity={dim ? 0.25 : 1} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} style={{ cursor: "default" }}>
              <title>{n.detail || n.label}{n.when ? ` · ${n.when}` : ""}</title>
              <circle r={r} fill={n.kind === "sender" || n.kind === "domain" || n.kind === "story" ? "var(--danger-soft)" : n.kind === "brand" || n.kind === "knowledge" ? "var(--chip)" : FILL[n.kind]} stroke={FILL[n.kind]} strokeWidth={2} strokeDasharray={n.kind === "sender" ? "4 3" : undefined} />
              {(n.kind === "member" || n.kind === "guardian") && <text y="7" textAnchor="middle" fontSize="20" fill="#fff" fontFamily="'Young Serif', serif">{n.label[0]}</text>}
              <text y={r + 14} textAnchor="middle" fontSize={n.kind === "brand" || n.kind === "knowledge" ? 10.5 : 12} fill="var(--fg)" fontFamily="Figtree, sans-serif" fontWeight={n.kind === "member" || n.kind === "guardian" ? 700 : 500}>{n.label.length > 26 ? n.label.slice(0, 25) + "…" : n.label}</text>
            </g>
          );
        })}
      </svg>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 12, color: "var(--muted)", alignItems: "center" }}>
        <span><i style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#2E46E5", marginRight: 6 }} />family</span>
        <span><i style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "var(--danger-soft)", border: "2px solid #D7322A", marginRight: 6 }} />seen and judged a scam</span>
        <span><i style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "var(--chip)", border: "2px solid #4A5170", marginRight: 6 }} />knowledge Guardian was given</span>
        {g && <span style={{ marginLeft: "auto" }}>SurrealDB Agent Memory{g.tier ? ` · ${g.tier}` : ""}{g.trace_id ? ` · trace ${g.trace_id}` : ""}</span>}
      </div>
    </div>
  );
}
