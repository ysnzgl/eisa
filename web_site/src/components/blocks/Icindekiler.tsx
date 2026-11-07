"use client";

/**
 * Zengin metin için yapışkan "İçindekiler" menüsü. Görünür bölümü vurgular,
 * tıklamada header offset'li kaydırır.
 */

import { useEffect, useState } from "react";
import { hedefeKaydir } from "@/lib/kaydirma";
import { cn } from "@/lib/utils";

export interface IcindekilerOgesi {
  id: string;
  metin: string;
  seviye: 2 | 3;
}

export function Icindekiler({ ogeler }: { ogeler: IcindekilerOgesi[] }) {
  const [aktif, setAktif] = useState<string | null>(ogeler[0]?.id ?? null);

  useEffect(() => {
    const elemanlar = ogeler
      .map((o) => document.getElementById(o.id))
      .filter((e): e is HTMLElement => Boolean(e));
    if (!elemanlar.length) return;
    const io = new IntersectionObserver(
      (girdiler) => {
        const gorunen = girdiler.filter((g) => g.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (gorunen[0]) setAktif(gorunen[0].target.id);
      },
      { rootMargin: "-15% 0px -70% 0px" },
    );
    elemanlar.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, [ogeler]);

  return (
    <nav aria-label="İçindekiler">
      <p className="eyebrow mb-4 text-zemin-soluk">İçindekiler</p>
      <ol className="space-y-1 border-l border-zemin-cizgi">
        {ogeler.map((o) => (
          <li key={o.id}>
            <a
              href={`#${o.id}`}
              onClick={(e) => {
                e.preventDefault();
                if (hedefeKaydir(o.id)) window.history.replaceState(null, "", `#${o.id}`);
              }}
              aria-current={aktif === o.id ? "location" : undefined}
              className={cn(
                "-ml-px block border-l-2 py-1.5 text-sm leading-snug transition-colors duration-300",
                o.seviye === 3 ? "pl-7" : "pl-4",
                aktif === o.id
                  ? "border-primary font-medium text-zemin-baslik"
                  : "border-transparent text-zemin-soluk hover:border-zemin-cizgi hover:text-zemin-baslik",
              )}
            >
              {o.metin}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}