"use client";

/**
 * scroll_hikaye istemci kısmı.
 * - Geniş ekran + hareket açık: bölüm sabitlenir (sticky); kaydırdıkça aktif adım değişir ve
 *   sağdaki kiosk ekranı o adımı gösterir. Adımlara tıklayınca ilgili konuma kaydırır.
 * - Mobil / reduced-motion: sabitleme yok; dikey zaman çizelgesi + her adımda küçük ekran kartı.
 * SSR'da dikey düzen render edilir; hidrasyondan sonra geniş ekranda sabitli düzene geçer.
 */

import { motion, useMotionValueEvent, useScroll } from "motion/react";
import { useRef, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { Reveal } from "@/components/ui/Reveal";
import { useAzHareket, useGenisEkran } from "@/lib/hooks";
import { lenisGetir } from "@/lib/kaydirma";
import type { ScrollHikayeAdimi } from "@/lib/types";
import { cn } from "@/lib/utils";
import { KioskMockup } from "./KioskMockup";

const ADIM_IKONLARI = ["Receipt", "DeviceMobile", "Sparkle", "ShieldCheck", "QrCode", "CheckCircle"];

export function ScrollHikayeIstemci({ adimlar }: { adimlar: ScrollHikayeAdimi[] }) {
  const genis = useGenisEkran();
  const azHareket = useAzHareket();
  if (!adimlar.length) return null;
  return genis && !azHareket ? <Sabitli adimlar={adimlar} /> : <Dikey adimlar={adimlar} />;
}

function Sabitli({ adimlar }: { adimlar: ScrollHikayeAdimi[] }) {
  const kap = useRef<HTMLDivElement>(null);
  const n = adimlar.length;
  const [aktif, setAktif] = useState(0);
  const { scrollYProgress } = useScroll({ target: kap, offset: ["start start", "end end"] });

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    const i = Math.min(n - 1, Math.max(0, Math.floor(v * n)));
    setAktif((onceki) => (onceki === i ? onceki : i));
  });

  const adimaGit = (i: number) => {
    const el = kap.current;
    if (!el) return;
    const ust = el.getBoundingClientRect().top + window.scrollY;
    const aralik = Math.max(0, el.offsetHeight - window.innerHeight);
    const hedef = ust + aralik * ((i + 0.5) / n);
    const lenis = lenisGetir();
    if (lenis) lenis.scrollTo(hedef, { force: true });
    else window.scrollTo({ top: hedef, behavior: "smooth" });
  };

  const adim = adimlar[aktif];

  return (
    <div ref={kap} className="relative" style={{ height: `${n * 70 + 40}vh` }}>
      <div className="sticky top-[calc(var(--header-yukseklik-dar)+var(--onizleme-bant))] flex h-[calc(100svh-var(--header-yukseklik-dar)-var(--onizleme-bant))] items-center">
        <div className="grid w-full grid-cols-12 items-center gap-10">
          <ol className="relative col-span-7 space-y-2">
            <span aria-hidden className="absolute top-8 bottom-8 left-[2.375rem] w-px bg-zemin-cizgi" />
            <motion.span
              aria-hidden
              style={{ scaleY: scrollYProgress }}
              className="absolute top-8 bottom-8 left-[2.375rem] w-px origin-top bg-primary"
            />
            {adimlar.map((a, i) => {
              const secili = i === aktif;
              return (
                <li key={i}>
                  <button
                    type="button"
                    onClick={() => adimaGit(i)}
                    aria-current={secili ? "step" : undefined}
                    className={cn(
                      "relative flex w-full items-start gap-5 rounded-kart p-4 text-left transition-[background-color,box-shadow] duration-500",
                      secili ? "bg-zemin-kart shadow-kart" : "hover:bg-zemin-kart/60",
                    )}
                  >
                    <span
                      className={cn(
                        "relative z-10 flex size-11 shrink-0 items-center justify-center rounded-full border font-display text-sm font-bold transition-all duration-500",
                        i <= aktif
                          ? "border-primary bg-primary text-white shadow-cta"
                          : "border-zemin-cizgi bg-zemin-kart text-zemin-soluk",
                      )}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="pt-2">
                      <span
                        className={cn(
                          "block font-display text-xl font-semibold transition-colors duration-500",
                          secili ? "text-zemin-baslik" : "text-zemin-soluk",
                        )}
                      >
                        {a.baslik}
                      </span>
                      <span
                        className={cn(
                          "grid transition-all duration-500 ease-eisa",
                          secili ? "mt-2 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                        )}
                      >
                        <span className="overflow-hidden leading-relaxed text-zemin-metin">{a.metin}</span>
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          <div className="col-span-5">
            <KioskMockup
              mod="kontrollu"
              adim={aktif}
              toplam={n}
              ekran={{ baslik: adim.ekran_baslik, metin: adim.ekran_metin }}
              ikon={ADIM_IKONLARI[aktif % ADIM_IKONLARI.length]}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function Dikey({ adimlar }: { adimlar: ScrollHikayeAdimi[] }) {
  return (
    <ol className="relative mx-auto max-w-2xl space-y-10">
      <span aria-hidden className="absolute top-2 bottom-2 left-[1.375rem] w-px bg-linear-to-b from-primary via-primary/40 to-zemin-cizgi" />
      {adimlar.map((a, i) => (
        <li key={i} className="relative pl-16">
          <span className="absolute top-0 left-0 flex size-11 items-center justify-center rounded-full bg-primary font-display text-sm font-bold text-white shadow-cta">
            {String(i + 1).padStart(2, "0")}
          </span>
          <Reveal>
            <h3 className="pt-2 font-display text-xl font-semibold text-zemin-baslik">{a.baslik}</h3>
            {a.metin ? <p className="mt-2 leading-relaxed text-zemin-metin">{a.metin}</p> : null}
            {a.ekran_baslik ? (
              <div className="mt-4 flex items-center gap-4 rounded-2xl border border-zemin-cizgi bg-zemin-kart p-4 shadow-kart">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-primary to-[#b5121a] text-white">
                  <Icon ad={ADIM_IKONLARI[i % ADIM_IKONLARI.length]} boyut={22} className="text-white" />
                </span>
                <span>
                  <span className="block text-sm font-semibold text-zemin-baslik">{a.ekran_baslik}</span>
                  {a.ekran_metin ? <span className="mt-0.5 block text-sm text-zemin-soluk">{a.ekran_metin}</span> : null}
                </span>
              </div>
            ) : null}
          </Reveal>
        </li>
      ))}
    </ol>
  );
}