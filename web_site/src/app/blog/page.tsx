/**
 * Blog listesi: /blog?kategori=<slug>&sayfa=<n>
 * searchParams kullandığı için istek anında render edilir; veri `blog` tag'i + 300 sn ile önbelleklidir.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "@phosphor-icons/react/dist/ssr/ArrowLeft";
import { ArrowRightIcon } from "@phosphor-icons/react/dist/ssr/ArrowRight";
import { WarningCircleIcon } from "@phosphor-icons/react/dist/ssr/WarningCircle";
import { BlogKart } from "@/components/blog/BlogKart";
import { SayfaUstu } from "@/components/SayfaUstu";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { getBlogListe, getSite, ogGorselleri, SLUG_DESENI } from "@/lib/api";
import type { BlogListe } from "@/lib/types";
import { cn } from "@/lib/utils";

const SAYFA_BOYUTU = 9;

type Arama = { kategori?: string | string[]; sayfa?: string | string[] };

function parametreler(arama: Arama): { kategori?: string; sayfa: number } {
  const k = Array.isArray(arama.kategori) ? arama.kategori[0] : arama.kategori;
  const s = Array.isArray(arama.sayfa) ? arama.sayfa[0] : arama.sayfa;
  const sayfa = Math.max(1, Number.parseInt(s ?? "1", 10) || 1);
  return { kategori: k && SLUG_DESENI.test(k) ? k : undefined, sayfa };
}

function blogHref(kategori: string | undefined, sayfa = 1): string {
  const qs = new URLSearchParams();
  if (kategori) qs.set("kategori", kategori);
  if (sayfa > 1) qs.set("sayfa", String(sayfa));
  const s = qs.toString();
  return s ? `/blog?${s}` : "/blog";
}

export async function generateMetadata({ searchParams }: { searchParams: Promise<Arama> }): Promise<Metadata> {
  const { kategori, sayfa } = parametreler(await searchParams);
  let kategoriAdi: string | undefined;
  if (kategori) {
    try {
      kategoriAdi = (await getBlogListe({ kategori, sayfa, boyut: SAYFA_BOYUTU })).kategoriler.find(
        (k) => k.slug === kategori,
      )?.ad;
    } catch {
      kategoriAdi = undefined;
    }
  }
  const baslik = kategoriAdi ? `${kategoriAdi} — Blog` : "Blog";
  const { ayarlar } = await getSite();
  const gorseller = ogGorselleri(null, ayarlar, baslik);
  return {
    title: sayfa > 1 ? `${baslik} (Sayfa ${sayfa})` : baslik,
    description:
      "Sağlık okuryazarlığı, eczane yönetimi ve e-isa'dan duyurular: eczacılar için sade ve temkinli yazılar.",
    alternates: { canonical: blogHref(kategori, sayfa) },
    openGraph: {
      type: "website",
      locale: "tr_TR",
      siteName: ayarlar.site_adi,
      title: baslik,
      url: blogHref(kategori, sayfa),
      images: gorseller,
    },
    twitter: { card: "summary_large_image", images: gorseller.map((g) => g.url) },
  };
}

export default async function BlogSayfasi({ searchParams }: { searchParams: Promise<Arama> }) {
  const { kategori, sayfa } = parametreler(await searchParams);

  let liste: BlogListe | null = null;
  try {
    liste = await getBlogListe({ kategori, sayfa, boyut: SAYFA_BOYUTU });
  } catch (hata) {
    console.error("[e-isa blog] liste alınamadı:", hata instanceof Error ? hata.message : hata);
  }

  return (
    <>
      <SayfaUstu>
        <Reveal className="text-center">
          <p className="eyebrow mb-5 inline-flex items-center gap-2 text-zemin-vurgu">
            <span aria-hidden className="size-1.5 rounded-full bg-primary" />
            e-isa Blog
          </p>
          <h1 className="text-4xl font-bold text-white sm:text-5xl lg:text-6xl">
            Eczane ve sağlık okuryazarlığı üzerine <span className="metin-gradyan">yazılar</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-white/70">
            Eczacının danışmanlık rolünü güçlendiren fikirler, pilot süreçten notlar ve e-isa&apos;dan haberler.
          </p>
        </Reveal>
      </SayfaUstu>

      <Section arka_plan="acik" padding="normal" aria-label="Blog yazıları">
        {liste && liste.kategoriler.length ? (
          <nav aria-label="Blog kategorileri" className="mb-12 flex flex-wrap justify-center gap-2">
            {[{ ad: "Tümü", slug: "" }, ...liste.kategoriler].map((k) => {
              const aktif = (kategori ?? "") === k.slug;
              return (
                <Link
                  key={k.slug || "tumu"}
                  href={blogHref(k.slug || undefined)}
                  aria-current={aktif ? "page" : undefined}
                  scroll={false}
                  className={cn(
                    "rounded-full border px-4 py-2 text-sm font-medium transition-colors",
                    aktif
                      ? "border-dark bg-dark text-white"
                      : "border-line bg-card text-ink hover:border-primary/40 hover:text-primary-hover",
                  )}
                >
                  {k.ad}
                </Link>
              );
            })}
          </nav>
        ) : null}

        {!liste ? (
          <div role="alert" className="mx-auto flex max-w-xl flex-col items-center rounded-kart border border-line bg-card p-10 text-center">
            <WarningCircleIcon aria-hidden size={40} weight="duotone" className="text-primary" />
            <p className="mt-4 text-lg font-semibold text-dark">Yazılar şu anda yüklenemedi.</p>
            <p className="mt-2 text-muted">Lütfen biraz sonra tekrar deneyin.</p>
          </div>
        ) : liste.sonuclar.length === 0 ? (
          <p className="mx-auto max-w-xl rounded-kart border border-dashed border-line p-10 text-center text-muted">
            {kategori ? "Bu kategoride henüz yazı yok." : "Henüz yayınlanmış yazı yok."}
          </p>
        ) : (
          <Stagger as="ul" key={`${kategori ?? ""}-${liste.sayfa}`} className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {liste.sonuclar.map((y) => (
              <StaggerItem as="li" key={y.slug}>
                <BlogKart yazi={y} baslikSeviyesi="h2" />
              </StaggerItem>
            ))}
          </Stagger>
        )}

        {liste && liste.sayfa_sayisi > 1 ? (
          <nav aria-label="Sayfalama" className="mt-14 flex items-center justify-center gap-2">
            {liste.sayfa > 1 ? (
              <Link
                href={blogHref(kategori, liste.sayfa - 1)}
                className="inline-flex h-10 items-center gap-1.5 rounded-full border border-line bg-card px-4 text-sm font-medium hover:border-primary/40"
              >
                <ArrowLeftIcon aria-hidden weight="bold" className="size-4" />
                Önceki
              </Link>
            ) : null}
            <ul className="flex items-center gap-1">
              {Array.from({ length: liste.sayfa_sayisi }, (_, i) => i + 1).map((n) => (
                <li key={n}>
                  <Link
                    href={blogHref(kategori, n)}
                    aria-current={n === liste.sayfa ? "page" : undefined}
                    aria-label={`Sayfa ${n}`}
                    className={cn(
                      "inline-flex size-10 items-center justify-center rounded-full text-sm font-semibold",
                      n === liste.sayfa ? "bg-dark text-white" : "text-ink hover:bg-gri",
                    )}
                  >
                    {n}
                  </Link>
                </li>
              ))}
            </ul>
            {liste.sayfa < liste.sayfa_sayisi ? (
              <Link
                href={blogHref(kategori, liste.sayfa + 1)}
                className="inline-flex h-10 items-center gap-1.5 rounded-full border border-line bg-card px-4 text-sm font-medium hover:border-primary/40"
              >
                Sonraki
                <ArrowRightIcon aria-hidden weight="bold" className="size-4" />
              </Link>
            ) : null}
          </nav>
        ) : null}
      </Section>
    </>
  );
}
