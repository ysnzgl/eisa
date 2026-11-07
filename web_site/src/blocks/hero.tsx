/**
 * hero — Hero (Anasayfa). CONTRACT §8.
 * Koyu zemin + AI ağı canvas + kelime kelime beliren başlık + animasyonlu kiosk mockup.
 * Metinler CSS giriş animasyonuyla sunucuda render edilir (LCP hidrasyonu beklemez).
 */

import type { CSSProperties } from "react";
import { AiAgi } from "@/components/blocks/AiAgi";
import { KelimeBaslik, kelimeAnimasyonSuresi } from "@/components/blocks/KelimeBaslik";
import { KioskMockup } from "@/components/blocks/KioskMockup";
import { ButonGrubu } from "@/components/ui/ButonLink";
import { GradientBackdrop, NoiseOverlay } from "@/components/ui/Dekor";
import { Icon } from "@/components/ui/Icon";
import { Section } from "@/components/ui/Section";
import type { HeroVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

export default function Hero({ veri, blokId }: BlokProps<HeroVeri>) {
  const baslikId = `${blokId}-baslik`;
  const kiosk = veri.kiosk_animasyonu !== false;
  const sonra = kelimeAnimasyonSuresi(veri.baslik, 0.15) - 0.2;
  const gecikme = (ek: number) => ({ "--gecikme": `${(sonra + ek).toFixed(2)}s` }) as CSSProperties;

  return (
    <Section
      arka_plan="koyu"
      padding="yok"
      aria-labelledby={baslikId}
      className="flex min-h-[100svh] flex-col overflow-hidden pt-[calc(var(--header-yukseklik)+var(--onizleme-bant)+3rem)] pb-24 md:pb-28"
      containerClassName="flex flex-1 items-center"
    >
      <GradientBackdrop varyant="koyu" izgara />
      <div aria-hidden className="absolute inset-0 -z-10 opacity-80">
        <AiAgi />
      </div>
      <NoiseOverlay />

      <div className="grid w-full items-center gap-16 py-6 lg:grid-cols-12 lg:gap-8">
        <div className={cn(kiosk ? "lg:col-span-7" : "mx-auto max-w-4xl text-center lg:col-span-12")}>
          {veri.rozet ? (
            <p className="giris mb-7 inline-flex items-center gap-2.5 rounded-full border border-white/15 bg-white/[0.06] px-4 py-1.5 text-sm font-medium text-white/85 backdrop-blur-sm">
              <span aria-hidden className="relative flex size-2">
                <span className="absolute inset-0 animate-nabiz rounded-full bg-primary" />
                <span className="relative size-2 rounded-full bg-primary" />
              </span>
              {veri.rozet}
            </p>
          ) : null}

          <KelimeBaslik
            as="h1"
            id={baslikId}
            metin={veri.baslik}
            vurgu={veri.vurgu}
            baslangic={0.15}
            className="text-[2.5rem] leading-[1.05] font-bold text-white sm:text-6xl lg:text-[4.1rem]"
          />

          {veri.alt_metin ? (
            <p
              className={cn("giris mt-7 max-w-2xl text-lg leading-relaxed text-white/70 md:text-xl", !kiosk && "mx-auto")}
              style={gecikme(0)}
            >
              {veri.alt_metin}
            </p>
          ) : null}

          {veri.vurgu_kartlari?.length ? (
            <ul className="mt-9 grid gap-3 text-left sm:grid-cols-2">
              {veri.vurgu_kartlari.map((k, i) => (
                <li
                  key={i}
                  style={gecikme(0.1 + i * 0.07)}
                  className="giris flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm font-medium text-white/85 backdrop-blur-sm transition-colors duration-300 hover:border-primary/40 hover:bg-white/[0.07]"
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/15 ring-1 ring-primary/25">
                    <Icon ad={k.ikon} boyut={20} className="text-[#ff5a60]" />
                  </span>
                  {k.metin}
                </li>
              ))}
            </ul>
          ) : null}

          {veri.butonlar?.length ? (
            <div className="giris mt-10" style={gecikme(0.4)}>
              <ButonGrubu butonlar={veri.butonlar} boyut="buyuk" className={kiosk ? undefined : "justify-center"} />
            </div>
          ) : null}
        </div>

        {kiosk ? (
          <div className="giris relative lg:col-span-5" style={gecikme(0)}>
            <KioskMockup mod="dongu" />
            <div
              aria-hidden
              className="cam-koyu absolute top-[16%] -left-1 hidden animate-yuzme items-center gap-2 rounded-2xl border border-white/10 px-3.5 py-2.5 text-xs font-semibold text-white shadow-koyu sm:flex lg:-left-6"
            >
              <Icon ad="Package" boyut={18} className="text-[#ff5a60]" />
              Marka değil, kategori
            </div>
            <div
              aria-hidden
              style={{ animationDelay: "-3s" }}
              className="cam-koyu absolute right-0 bottom-[24%] hidden animate-yuzme items-center gap-2 rounded-2xl border border-white/10 px-3.5 py-2.5 text-xs font-semibold text-white shadow-koyu sm:flex lg:-right-4"
            >
              <Icon ad="ShieldCheck" boyut={18} className="text-[#ff5a60]" />
              Son karar eczacıda
            </div>
          </div>
        ) : null}
      </div>

      <div aria-hidden className="absolute bottom-7 left-1/2 hidden -translate-x-1/2 md:block">
        <div className="flex h-10 w-6 justify-center rounded-full border border-white/25 pt-2">
          <span className="block h-2 w-1 animate-kaydir-ipucu rounded-full bg-white/70" />
        </div>
      </div>
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-px bg-linear-to-r from-transparent via-primary/60 to-transparent"
      />
    </Section>
  );
}