"use client";

/**
 * Çerez bilgilendirme bandı. Şu an analitik/pazarlama çerezi YOK; yalnızca zorunlu çerezler
 * hakkında bilgi verir. "Anladım" tercihi localStorage'da saklanır.
 * İleride analitik eklenirse: buraya "Kabul et / Reddet" eklenip analitik yalnızca onayla yüklenmeli.
 */

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { CookieIcon } from "@phosphor-icons/react/dist/ssr/Cookie";
import { AkilliLink } from "@/components/ui/AkilliLink";
import { butonSiniflari } from "@/components/ui/ButonLink";
import { EASE_EISA } from "@/lib/hareket";
import { useAzHareket, useHidrasyonTamam } from "@/lib/hooks";

const ANAHTAR = "eisa_cerez_bilgi";

function kayitliMi(): boolean {
  try {
    return window.localStorage.getItem(ANAHTAR) === "1";
  } catch {
    return false;
  }
}

export function CookieBanner({ politikaHref = "/cerez-politikasi" }: { politikaHref?: string }) {
  const hidrasyonTamam = useHidrasyonTamam();
  const azHareket = useAzHareket();
  const [kapatildi, setKapatildi] = useState(false);
  const goster = hidrasyonTamam && !kapatildi && !kayitliMi();

  const anladim = () => {
    try {
      window.localStorage.setItem(ANAHTAR, "1");
    } catch {
      // Gizli mod vb.: yalnızca bu oturum için kapat.
    }
    setKapatildi(true);
  };

  return (
    <AnimatePresence>
      {goster ? (
        <motion.section
          aria-label="Çerez bilgilendirmesi"
          initial={azHareket ? { opacity: 0 } : { opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          exit={azHareket ? { opacity: 0 } : { opacity: 0, y: 40 }}
          transition={{ duration: azHareket ? 0 : 0.5, ease: EASE_EISA, delay: azHareket ? 0 : 0.8 }}
          className="fixed inset-x-3 bottom-3 z-[60] mx-auto max-w-3xl sm:inset-x-6 sm:bottom-6"
        >
          <div
            data-zemin="koyu"
            className="cam-koyu flex flex-col gap-4 rounded-2xl border border-white/10 p-4 text-white shadow-koyu sm:flex-row sm:items-center sm:gap-5 sm:p-5"
          >
            <span className="hidden size-11 shrink-0 items-center justify-center rounded-full bg-white/10 sm:inline-flex">
              <CookieIcon aria-hidden size={22} weight="duotone" className="text-[#ff5a60]" />
            </span>
            <p className="text-sm leading-relaxed text-white/80">
              Sitemizde yalnızca sitenin çalışması için gerekli zorunlu çerezler kullanılır; analitik veya
              pazarlama çerezi kullanılmaz. Ayrıntılar için{" "}
              <AkilliLink href={politikaHref} className="font-medium text-white underline underline-offset-4 hover:text-[#ff5a60]">
                Çerez Politikası
              </AkilliLink>
              .
            </p>
            <button type="button" onClick={anladim} className={butonSiniflari("birincil", "kucuk", "shrink-0")}>
              Anladım
            </button>
          </div>
        </motion.section>
      ) : null}
    </AnimatePresence>
  );
}
