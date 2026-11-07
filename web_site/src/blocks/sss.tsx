/**
 * sss — SSS. CONTRACT §8.
 * Masaüstünde iki kolon (solda sabit başlık, sağda akordeon) + FAQPage JSON-LD.
 */

import { SssIstemci } from "@/components/blocks/SssIstemci";
import { JsonLd } from "@/components/JsonLd";
import { ButonLink } from "@/components/ui/ButonLink";
import { Reveal } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { SssVeri } from "@/lib/types";
import type { BlokProps } from "./types";

export default function Sss({ veri, blokId }: BlokProps<SssVeri>) {
  const sorular = (veri.sorular ?? []).filter((s) => s?.soru);
  if (!sorular.length) return null;
  const baslikId = `${blokId}-baslik`;

  return (
    <Section arka_plan={veri.arka_plan} aria-labelledby={baslikId}>
      <JsonLd
        veri={{
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: sorular.map((s) => ({
            "@type": "Question",
            name: s.soru,
            acceptedAnswer: { "@type": "Answer", text: s.cevap },
          })),
        }}
      />
      <div className="grid gap-10 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-4">
          <div className="lg:sticky lg:top-[calc(var(--header-yukseklik-dar)+var(--onizleme-bant)+2rem)]">
            <SectionHeading
              ust_baslik={veri.ust_baslik}
              baslik={veri.baslik}
              aciklama={veri.aciklama}
              baslikId={baslikId}
              hizalama="sol"
              altBosluk={false}
              className="mb-8"
            />
            <Reveal gecikme={0.1} className="hidden lg:block">
              <p className="text-sm text-zemin-soluk">Aradığınız yanıtı bulamadınız mı?</p>
              <ButonLink href="/iletisim" stil="hayalet" className="mt-1">
                Bize yazın
              </ButonLink>
            </Reveal>
          </div>
        </div>
        <Reveal gecikme={0.1} className="lg:col-span-8">
          <SssIstemci sorular={sorular} blokId={blokId} />
        </Reveal>
      </div>
    </Section>
  );
}