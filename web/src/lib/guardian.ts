"use client";
import { useEffect, useMemo, useReducer, useState } from "react";

export const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8787").replace(/\/$/, "");

export type GEvent = { t: number; kind: string; case: string | null; [k: string]: unknown };

export type Fired = { rule: string; weight: number; reason: string; reason_en?: string };
export type CaseState = {
  id: string;
  text?: string;
  lang?: string;
  protected?: string;
  sender?: string | null;
  quiet?: boolean;
  status: "open" | "closed";
  verdict?: { score: number; label: "safe" | "suspicious" | "scam"; reasons: string[]; fired: Fired[] };
  detonation?: Record<string, unknown> & { screenshot_url?: string; final_domain?: string; redirects?: string[]; form_fields?: string[]; domain_age_days?: number; sandbox_destroyed_s?: number; sandbox_id?: string; mode?: string; browser?: string };
  liveView?: string | null;
  money?: { amount: number; method: string; state: "locked" | "declined" | "approved"; guardian?: string };
  calls: Record<string, { status: string; lines: { role: string; text: string }[] }>;
  verify?: string;
  teachback?: boolean;
  help?: { steps: string[]; title: string; audio_url?: string | null };
  evals?: Record<string, boolean>;
  timeToCall?: number | null;
  memory?: { hits: { text: string; when: string; score: number }[]; trace_id?: string | null; tier?: string | null; prior_scam?: { what: string; date: string } | null };
};

export type State = { cases: Record<string, CaseState>; order: string[]; sms: GEvent[]; connected: boolean; last?: GEvent };

const init: State = { cases: {}, order: [], sms: [], connected: false };

function reduce(s: State, e: GEvent | { kind: "__conn"; ok: boolean }): State {
  if (e.kind === "__conn") return { ...s, connected: (e as { ok: boolean }).ok };
  const ev = e as GEvent;
  if (ev.kind === "ping") return s;
  const next: State = { ...s, last: ev };
  if (ev.kind === "sms.in" || ev.kind === "sms.out") next.sms = [...s.sms, ev].slice(-60);
  const id = ev.case;
  if (!id) return next;
  const prev: CaseState = s.cases[id] || { id, status: "open", calls: {} };
  const c: CaseState = { ...prev, calls: { ...prev.calls } };
  const k = ev.kind;
  if (k === "case.opened") { c.text = ev.text as string; c.lang = ev.lang as string; c.protected = ev.protected as string; c.sender = (ev.sender as string | null) ?? null; c.quiet = !!ev.quiet; }
  else if (k === "verdict") c.verdict = ev as unknown as CaseState["verdict"];
  else if (k === "detonation.live") c.liveView = (ev.live_view_url as string) || null;
  else if (k === "detonation.result") c.detonation = ev as CaseState["detonation"];
  else if (k === "money.locked") c.money = { amount: ev.amount as number, method: ev.method as string, state: "locked", guardian: ev.guardian as string };
  else if (k === "key.decision" && c.money) c.money = { ...c.money, state: ev.decision === "decline" ? "declined" : "approved" };
  else if (k === "verify.outcome") c.verify = ev.outcome as string;
  else if (k === "teachback") c.teachback = ev.ok as boolean;
  else if (k === "help.note.ready") c.help = { steps: ev.steps as string[], title: ev.title as string, audio_url: ev.audio_url as string | null };
  else if (k === "eval.live") c.evals = { grounded: !!ev.grounded, no_asks: !!ev.no_asks, language: !!ev.language };
  else if (k === "memory.recalled") c.memory = { hits: (ev.hits as { text: string; when: string; score: number }[]) || [], trace_id: ev.trace_id as string | null, tier: ev.tier as string | null, prior_scam: (ev.prior_scam as { what: string; date: string } | null) ?? null };
  else if (k === "case.closed") { c.status = "closed"; c.timeToCall = ev.time_to_call_s as number | null; }
  else if (k.startsWith("call.")) {
    const [, call, phase] = k.split(".");
    const cur = c.calls[call] || { status: "idle", lines: [] };
    if (phase === "transcript") c.calls[call] = { ...cur, lines: [...cur.lines, { role: ev.role as string, text: ev.text as string }] };
    else c.calls[call] = { ...cur, status: phase === "ended" ? String(ev.status) : phase };
  }
  next.cases = { ...s.cases, [id]: c };
  next.order = s.order.includes(id) ? s.order : [...s.order, id];
  return next;
}

/** One live connection to the backend. Every screen derives what it shows from these events. */
export function useGuardian() {
  const [state, dispatch] = useReducer(reduce, init);
  useEffect(() => {
    const es = new EventSource(`${API}/events`);
    es.onopen = () => dispatch({ kind: "__conn", ok: true });
    es.onerror = () => dispatch({ kind: "__conn", ok: false }); // EventSource retries by itself
    es.onmessage = (m) => { try { dispatch(JSON.parse(m.data)); } catch {} };
    return () => es.close();
  }, []);
  const latest = useMemo(() => (state.order.length ? state.cases[state.order[state.order.length - 1]] : undefined), [state]);
  return { ...state, latest };
}

export type Lang = "en" | "te" | "es";
export const LANG_NAME: Record<string, string> = { en: "English", te: "Telugu", es: "Spanish" };

export type Beat = "link" | "family" | "money" | "support";
/** dry=true rehearses the beat with every sponsor mocked for that one case: no texts, no calls, no sandbox. */
export async function fireDemo(beat: Beat, lang: Lang = "en", dry = false) {
  return fetch(`${API}/demo/${beat}?lang=${lang}${dry ? "&dry=1" : ""}`, { method: "POST" }).then((r) => r.json());
}

export async function turnKey(caseId: string, decision: "approve" | "decline") {
  return fetch(`${API}/cases/${caseId}/key`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ decision }) }).then((r) => r.json());
}

export function useHealth() {
  const [h, setH] = useState<{ live?: Record<string, boolean> } | null>(null);
  useEffect(() => { fetch(`${API}/health`).then((r) => r.json()).then(setH).catch(() => setH(null)); }, []);
  return h;
}
