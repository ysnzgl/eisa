/**
 * scroll_hikaye — Scroll Hikâye (Kiosk). CONTRACT §8.
 * Masaüstünde sabitlenen bölüm: kaydırdıkça adımlar ilerler, kiosk ekranı değişir.
 * Mantık: components/blocks/ScrollHikayeIstemci.tsx
 */

import { ScrollHikayeIstemci } from "@/components/blocks/ScrollHikayeIstemci";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { ScrollHikayeVeri } from "@/lib/types";
import type { BlokProps } from "./types";

export default function ScrollHikaye({ veri, blokId }: BlokProps<ScrollHikayeVeri>) {
  const baslikId = `${blokId}-baslik`;
  return (
    <Section arka_plan="gri" aria-labelledby={baslikId}>
      <SectionHeading ust_baslik={veri.ust_baslik} baslik={veri.baslik} aciklama={veri.aciklama} baslikId={baslikId} />
      <ScrollHikayeIstemci adimlar={veri.adimlar ?? []} />
    </Section>
  );
}