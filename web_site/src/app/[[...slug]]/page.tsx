/**
 * Blok tabanlı CMS sayfaları: `/` (anasayfa) ve `/<slug>`.
 *
 * ISR: sayfalar ilk istekte üretilir ve önbelleğe alınır (revalidate 3600 sn + `sayfa:<slug>` tag'i).
 * Build sırasında backend kapalıysa generateStaticParams [] döner → build kırılmaz.
 */

import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { BlockRenderer, koyuUstMu } from "@/blocks";
import { getSayfa, getSayfaListesi, getSite, ogGorselleri, SLUG_DESENI } from "@/lib/api";
import { slugYolu } from "@/lib/utils";

export const revalidate = 3600;
export const dynamicParams = true;

type Params = { slug?: string[] };

/** URL parçalarından CMS slug'ı. Geçersizse null (→ 404). */
function slugCoz(parcalar: string[] | undefined): string | null {
  if (!parcalar || parcalar.length === 0) return "anasayfa";
  if (parcalar.length > 1) return null;
  const slug = decodeURIComponent(parcalar[0]);
  return SLUG_DESENI.test(slug) ? slug : null;
}

export async function generateStaticParams(): Promise<Params[]> {
  try {
    const liste = await getSayfaListesi();
    return liste
      .filter((s) => SLUG_DESENI.test(s.slug))
      .map((s) => ({ slug: s.slug === "anasayfa" ? [] : [s.slug] }));
  } catch (hata) {
    console.warn(
      `[e-isa] generateStaticParams: sayfa listesi alınamadı, sayfalar istek anında üretilecek. (${
        hata instanceof Error ? hata.message : String(hata)
      })`,
    );
    return [];
  }
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const slug = slugCoz((await params).slug);
  if (!slug) notFound();
  const [sayfa, site] = await Promise.all([getSayfa(slug), getSite()]);
  if (!sayfa) notFound();

  const baslik = sayfa.seo?.baslik || sayfa.baslik;
  const aciklama = sayfa.seo?.aciklama || site.ayarlar.seo_aciklama;
  const yol = slugYolu(slug);
  const gorseller = ogGorselleri(sayfa.seo?.og_gorsel, site.ayarlar, baslik);

  return {
    // Layout'taki seo_baslik_sablonu uygulanır: "%s | e-isa"
    title: baslik,
    description: aciklama || undefined,
    alternates: { canonical: yol },
    openGraph: {
      type: "website",
      locale: "tr_TR",
      siteName: site.ayarlar.site_adi,
      title: baslik,
      description: aciklama || undefined,
      url: yol,
      images: gorseller,
    },
    twitter: { card: "summary_large_image", images: gorseller.map((g) => g.url) },
  };
}

export default async function CmsSayfasi({ params }: { params: Promise<Params> }) {
  const parcalar = (await params).slug;
  // /anasayfa → / (tek kanonik adres)
  if (parcalar?.length === 1 && parcalar[0] === "anasayfa") permanentRedirect("/");

  const slug = slugCoz(parcalar);
  if (!slug) notFound();

  const sayfa = await getSayfa(slug);
  if (!sayfa) notFound();

  const bloklar = sayfa.bloklar ?? [];
  const icerik = <BlockRenderer bloklar={bloklar} sayfaSlug={sayfa.slug} />;

  // Sayfa koyu başlık bloğuyla başlamıyorsa içerik sabit header'ın altında kalmasın.
  return koyuUstMu(bloklar) ? (
    icerik
  ) : (
    <div className="pt-[calc(var(--header-yukseklik)+var(--onizleme-bant))]">{icerik}</div>
  );
}
