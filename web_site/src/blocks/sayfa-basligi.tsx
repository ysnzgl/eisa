/**
 * sayfa_basligi — Sayfa Başlığı (iç sayfalar). CONTRACT §8.
 * Hero ile aynı görsel dil, daha kısa: koyu zemin, ızgara, yörünge dekoru, kelime animasyonlu h1.
 */

import type { CSSProperties } from "react";
import { CaretRightIcon } from "@phosphor-icons/react/dist/ssr/CaretRight";
import { KelimeBaslik, kelimeAnimasyonSuresi } from "@/components/blocks/KelimeBaslik";
import { ButonGrubu } from "@/components/ui/ButonLink";
import { GradientBackdrop, NoiseOverlay } from "@/components/ui/Dekor";
import { Section } from "@/components/ui/Section";
import type { SayfaBasligiVeri } from "@/lib/types";
import type { BlokProps } from "./types";

export default function SayfaBasligi({ veri, blokId }: BlokProps<SayfaBasligiVeri>) {
  const baslikId = `${blokId}-baslik`;
  const sonra = kelimeAnimasyonSuresi(veri.baslik, 0.1) - 0.2;
  const gecikme = (ek: number) => ({ "--gecikme": `${(sonra + ek).toFixed(2)}s` }) as CSSProperties;

  return (
    <Section
      arka_plan="koyu"
      padding="yok"
      aria-labelledby={baslikId}
      className="overflow-hidden pt-[calc(var(--header-yukseklik)+var(--onizleme-bant)+4.5rem)] pb-20 md:pt-[calc(var(--header-yukseklik)+var(--onizleme-bant)+6rem)] md:pb-28"
    >
      <GradientBackdrop varyant="koyu" izgara />
      <NoiseOverlay />

      {/* Yörünge dekoru */}
      <div aria-hidden className="absolute top-1/2 right-[-14rem] -z-10 hidden size-[38rem] -translate-y-1/2 lg:block">
        <div className="absolute inset-0 animate-yavas-don rounded-full border border-dashed border-white/12">
          <span className="absolute top-0 left-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_20px_4px_rgba(237,28,36,0.6)]" />
        </div>
        <div className="absolute inset-20 rounded-full border border-white/[0.06]" />
        <div className="absolute inset-40 rounded-full bg-primary/15 blur-3xl" />
      </div>

      <div className="max-w-4xl">
        {veri.rozet ? (
          <p className="giris mb-6 inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.05] px-4 py-1.5 text-sm font-medium text-white/60">
            <span>e-isa</span>
            <CaretRightIcon aria-hidden size={12} weight="bold" className="text-white/40" />
            <span className="text-white/90">{veri.rozet}</span>
          </p>
        ) : null}
        <KelimeBaslik
          as="h1"
          id={baslikId}
          metin={veri.baslik}
          vurgu={veri.vurgu}
          className="text-4xl leading-[1.08] font-bold text-white sm:text-5xl lg:text-6xl"
        />
        {veri.alt_metin ? (
          <p className="giris mt-6 max-w-2xl text-lg leading-relaxed text-white/70 md:text-xl" style={gecikme(0)}>
            {veri.alt_metin}
          </p>
        ) : null}
        {veri.butonlar?.length ? (
          <div className="giris mt-9" style={gecikme(0.2)}>
            <ButonGrubu butonlar={veri.butonlar} boyut="buyuk" />
          </div>
        ) : null}
      </div>

      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-px bg-linear-to-r from-transparent via-primary/60 to-transparent"
      />
    </Section>
  );
}