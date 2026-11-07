"use client";

/**
 * 404 / hata sayfaları için markalı, animasyonlu koyu sahne.
 * reduced-motion'da animasyonlar kapalı (CSS kuralları + motion süre 0).
 */

import { motion } from "motion/react";
import type { ReactNode } from "react";
import { EASE_EISA } from "@/lib/hareket";
import { useAzHareket } from "@/lib/hooks";

export interface HataSahnesiProps {
  /** Büyük gösterilecek kod, ör. "404" */
  kod: string;
  baslik: string;
  aciklama?: string;
  children?: ReactNode;
  /** h1 kullanılsın mı (varsayılan true) */
  anaBaslik?: boolean;
}

export function HataSahnesi({ kod, baslik, aciklama, children, anaBaslik = true }: HataSahnesiProps) {
  const azHareket = useAzHareket();
  const Baslik = anaBaslik ? "h1" : "h2";
  const gecis = (gecikme: number) => ({ duration: azHareket ? 0 : 0.8, delay: azHareket ? 0 : gecikme, ease: EASE_EISA });

  return (
    <div data-ilk-blok="koyu">
      <section
        data-zemin="koyu"
        className="relative isolate flex min-h-[88vh] items-center overflow-hidden bg-dark pt-[calc(var(--header-yukseklik)+var(--onizleme-bant)+2rem)] pb-24 text-white"
      >
        {/* Dekor: ızgara + parıltılar + yörünge */}
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="doku-izgara absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)]" />
          <div className="animate-parilti absolute top-1/4 left-1/2 h-[30rem] w-[30rem] -translate-x-1/2 rounded-full bg-primary/25 blur-[130px]" />
          <div className="absolute -bottom-40 -left-20 h-96 w-96 rounded-full bg-[#2b6cb0]/20 blur-[120px]" />
          <div className="animate-yavas-don absolute top-1/2 left-1/2 size-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-white/10">
            <span className="absolute -top-1.5 left-1/2 size-3 -translate-x-1/2 rounded-full bg-primary shadow-[0_0_20px_4px_rgb(237_28_36/0.6)]" />
          </div>
          <div className="absolute top-1/2 left-1/2 size-[22rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/5" />
        </div>

        <div className="container-eisa max-w-3xl text-center">
          <motion.p
            aria-hidden
            initial={azHareket ? false : { opacity: 0, scale: 0.85, filter: "blur(12px)" }}
            animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
            transition={gecis(0)}
            className="metin-gradyan font-display text-[7rem] leading-none font-bold tracking-tighter sm:text-[10rem]"
          >
            {kod}
          </motion.p>
          <motion.div
            initial={azHareket ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={gecis(0.2)}
          >
            <Baslik className="mt-4 text-3xl font-bold text-white sm:text-4xl">{baslik}</Baslik>
            {aciklama ? <p className="mx-auto mt-5 max-w-xl text-lg text-white/70">{aciklama}</p> : null}
          </motion.div>
          {children ? (
            <motion.div
              initial={azHareket ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={gecis(0.35)}
              className="mt-10 flex flex-wrap items-center justify-center gap-3"
            >
              {children}
            </motion.div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
