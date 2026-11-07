"use client";

/**
 * Erişilebilir SSS akordeonu: tek açık öğe, yumuşak yükseklik geçişi, + → × ikon dönüşü.
 * Kapalı paneller `inert` (klavye/ekran okuyucu odaklanmaz).
 */

import { useState } from "react";
import { Paragraflar } from "@/components/ui/Paragraflar";
import type { SssSorusu } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SssIstemci({ sorular, blokId }: { sorular: SssSorusu[]; blokId: string }) {
  const [acik, setAcik] = useState<number | null>(0);
  return (
    <ul className="divide-y divide-zemin-cizgi overflow-hidden rounded-panel border border-zemin-cizgi bg-zemin-kart shadow-kart">
      {sorular.map((s, i) => {
        const a = acik === i;
        const kimlik = `${blokId}-sss-${i}`;
        return (
          <li key={i} className={cn("transition-colors duration-300", a && "bg-primary/[0.025]")}>
            <h3>
              <button
                id={`${kimlik}-baslik`}
                type="button"
                aria-expanded={a}
                aria-controls={`${kimlik}-panel`}
                onClick={() => setAcik(a ? null : i)}
                className="group flex w-full items-center justify-between gap-6 px-6 py-5 text-left md:px-8 md:py-6"
              >
                <span
                  className={cn(
                    "font-display text-lg leading-snug font-semibold transition-colors duration-300",
                    a ? "text-zemin-vurgu" : "text-zemin-baslik group-hover:text-zemin-vurgu",
                  )}
                >
                  {s.soru}
                </span>
                <span
                  aria-hidden
                  className={cn(
                    "relative flex size-9 shrink-0 items-center justify-center rounded-full border transition-all duration-500 ease-eisa",
                    a ? "rotate-45 border-primary bg-primary text-white" : "border-zemin-cizgi text-zemin-soluk group-hover:border-primary/40",
                  )}
                >
                  <span className="absolute h-0.5 w-3.5 rounded-full bg-current" />
                  <span className="absolute h-3.5 w-0.5 rounded-full bg-current" />
                </span>
              </button>
            </h3>
            <div
              id={`${kimlik}-panel`}
              role="region"
              aria-labelledby={`${kimlik}-baslik`}
              inert={!a}
              className={cn(
                "grid transition-[grid-template-rows,opacity] duration-500 ease-eisa",
                a ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
              )}
            >
              <div className="overflow-hidden">
                <Paragraflar metin={s.cevap} className="px-6 pb-6 leading-relaxed text-zemin-metin md:px-8 md:pb-7" />
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}