"use client";
import { PhoneAmma } from "@/components/PhoneAmma";
import { useEffect, useState } from "react";
import { API, useGuardian } from "@/lib/guardian";

const NAME: Record<string, string> = { en: "Jasmine", te: "Amma", es: "Rosa" };
type FamMember = { name: string; role: string; lang: string; safe_phrase?: string | null };

/** A mirror of the protected member's phone, for a tablet or spare phone on the table next to the stage. */
export default function PhoneMirror() {
  const { latest: c, sms } = useGuardian();
  const lang = c?.lang || "en";
  const [members, setMembers] = useState<FamMember[]>([]);
  useEffect(() => { fetch(`${API}/family`).then((r) => r.json()).then((f) => setMembers(f.members || [])).catch(() => {}); }, []);
  const m = members.find((x) => x.role === "protected" && x.lang === lang);
  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ height: "min(92vh, 760px)", aspectRatio: "1 / 2", display: "flex" }}>
        <PhoneAmma c={c} sms={sms} who={c?.protected || m?.name || NAME[lang]} phrase={m?.safe_phrase || ""} />
      </div>
    </main>
  );
}
