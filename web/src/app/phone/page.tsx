"use client";
import { PhoneAmma } from "@/components/PhoneAmma";
import { useGuardian } from "@/lib/guardian";

const PHRASE: Record<string, string> = { en: "Buckie the dog", te: "Kanna", es: "flan de la abuela" };
const NAME: Record<string, string> = { en: "Jasmine", te: "Amma", es: "Rosa" };

/** A mirror of the protected member's phone, for a tablet or spare phone on the table next to the stage. */
export default function PhoneMirror() {
  const { latest: c, sms } = useGuardian();
  const lang = c?.lang || "en";
  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ height: "min(92vh, 760px)", aspectRatio: "1 / 2", display: "flex" }}>
        <PhoneAmma c={c} sms={sms} who={c?.protected || NAME[lang]} phrase={PHRASE[lang]} />
      </div>
    </main>
  );
}
