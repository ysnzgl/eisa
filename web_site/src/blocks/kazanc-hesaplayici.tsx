/**
 * kazanc_hesaplayici — Kazanç Hesaplayıcı. CONTRACT §8.
 * Rakamlar "örnek senaryo/potansiyel"dir; `uyari_notu` her zaman görünür.
 * Mantık: components/blocks/KazancIstemci.tsx
 */

import { KazancIstemci } from "@/components/blocks/KazancIstemci";
import { Reveal } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { KazancHesaplayiciVeri } from "@/lib/types";
import type { BlokProps } from "./types";

export default function KazancHesaplayici({ veri, blokId }: BlokProps<KazancHesaplayiciVeri>) {
  if (!veri.kademeler?.length) return null;
  const baslikId = `${blokId}-baslik`;
  return (
    <Section arka_plan="acik" aria-labelledby={baslikId}>
      <SectionHeading ust_baslik={veri.ust_baslik} baslik={veri.baslik} aciklama={veri.aciklama} baslikId={baslikId} />
      <Reveal>
        <KazancIstemci veri={veri} />
      </Reveal>
    </Section>
  );
}