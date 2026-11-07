/**
 * blog_son_yazilar — Son Blog Yazıları. CONTRACT §8.
 * Async server component: veriyi kendisi çeker (`getSonYazilar` — hata olursa [] döner, blok gizlenir).
 */

import { BlogKart } from "@/components/blog/BlogKart";
import { ButonLink } from "@/components/ui/ButonLink";
import { Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { getSonYazilar } from "@/lib/api";
import type { BlogSonYazilarVeri } from "@/lib/types";
import type { BlokProps } from "./types";

export default async function BlogSonYazilar({ veri, blokId }: BlokProps<BlogSonYazilarVeri>) {
  const adet = Math.min(6, Math.max(1, Number(veri.adet) || 3));
  const yazilar = await getSonYazilar(adet, veri.kategori_slug || undefined);
  if (!yazilar.length) return null;
  const baslikId = `${blokId}-baslik`;
  const tumu = veri.kategori_slug ? `/blog?kategori=${encodeURIComponent(veri.kategori_slug)}` : "/blog";

  return (
    <Section arka_plan="acik" aria-labelledby={veri.baslik ? baslikId : undefined}>
      <div className="mb-12 flex flex-col gap-6 md:mb-16 md:flex-row md:items-end md:justify-between">
        <SectionHeading baslik={veri.baslik} aciklama={veri.aciklama} baslikId={baslikId} hizalama="sol" altBosluk={false} />
        <ButonLink href={tumu} stil="ikincil" className="shrink-0 self-start md:self-auto">
          Tüm yazılar
        </ButonLink>
      </div>
      <Stagger as="ul" className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {yazilar.map((y) => (
          <StaggerItem as="li" key={y.slug}>
            <BlogKart yazi={y} />
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}