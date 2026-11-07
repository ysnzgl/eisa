/**
 * Blog yazısı detayı: /blog/<slug>
 * ISR (revalidate 3600 + `blog`, `blog:<slug>` tag'leri). Draft mode'da preview ucundan okunur.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeftIcon } from "@phosphor-icons/react/dist/ssr/ArrowLeft";
import { EnvelopeSimpleIcon } from "@phosphor-icons/react/dist/ssr/EnvelopeSimple";
import { LinkedinLogoIcon } from "@phosphor-icons/react/dist/ssr/LinkedinLogo";
import { WhatsappLogoIcon } from "@phosphor-icons/react/dist/ssr/WhatsappLogo";
import { XLogoIcon } from "@phosphor-icons/react/dist/ssr/XLogo";
import { BaglantiKopyala } from "@/components/blog/BaglantiKopyala";
import { BlogKart } from "@/components/blog/BlogKart";
import { JsonLd } from "@/components/JsonLd";
import { SayfaUstu } from "@/components/SayfaUstu";
import { MediaImage } from "@/components/ui/MediaImage";
import { Reveal } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { getBlogListe, getBlogYazisi, getSite, mediaUrl, ogGorselleri, siteUrl } from "@/lib/api";
import type { BlogOzet } from "@/lib/types";
import { tarihFormatla } from "@/lib/utils";

export const revalidate = 3600;
export const dynamicParams = true;

type Params = { slug: string };

export async function generateStaticParams(): Promise<Params[]> {
  try {
    const liste = await getBlogListe({ boyut: 24 });
    return liste.sonuclar.map((y) => ({ slug: y.slug }));
  } catch (hata) {
    console.warn(
      `[e-isa] blog generateStaticParams: liste alınamadı, yazılar istek anında üretilecek. (${
        hata instanceof Error ? hata.message : String(hata)
      })`,
    );
    return [];
  }
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const [yazi, site] = await Promise.all([getBlogYazisi(slug), getSite()]);
  if (!yazi) return {};
  const baslik = yazi.seo?.baslik || yazi.baslik;
  const aciklama = yazi.seo?.aciklama || yazi.ozet;
  const gorseller = ogGorselleri(yazi.seo?.og_gorsel ?? yazi.kapak, site.ayarlar, baslik);
  const yol = `/blog/${yazi.slug}`;
  return {
    title: baslik,
    description: aciklama || undefined,
    alternates: { canonical: yol },
    authors: yazi.yazar_adi ? [{ name: yazi.yazar_adi }] : undefined,
    keywords: yazi.etiketler?.length ? yazi.etiketler : undefined,
    openGraph: {
      type: "article",
      locale: "tr_TR",
      siteName: site.ayarlar.site_adi,
      title: baslik,
      description: aciklama || undefined,
      url: yol,
      publishedTime: yazi.yayin_tarihi,
      authors: yazi.yazar_adi ? [yazi.yazar_adi] : undefined,
      section: yazi.kategori?.ad,
      tags: yazi.etiketler,
      images: gorseller,
    },
    twitter: { card: "summary_large_image", images: gorseller.map((g) => g.url) },
  };
}

/** İlgili yazılar boşsa son yazılardan doldurur (hata olursa boş). */
async function digerYazilar(slug: string, ilgili: BlogOzet[]): Promise<BlogOzet[]> {
  if (ilgili?.length) return ilgili.slice(0, 3);
  try {
    const liste = await getBlogListe({ boyut: 4 });
    return liste.sonuclar.filter((y) => y.slug !== slug).slice(0, 3);
  } catch {
    return [];
  }
}

export default async function BlogYazisiSayfasi({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const yazi = await getBlogYazisi(slug);
  if (!yazi) notFound();

  const [site, digerleri] = await Promise.all([getSite(), digerYazilar(yazi.slug, yazi.ilgili)]);
  const url = siteUrl(`/blog/${yazi.slug}`);
  const kapakUrl = yazi.kapak ? mediaUrl(yazi.kapak.yol) : null;
  const metinUrl = encodeURIComponent(url);
  const metinBaslik = encodeURIComponent(yazi.baslik);

  const paylasim = [
    { ad: "LinkedIn'de paylaş", href: `https://www.linkedin.com/sharing/share-offsite/?url=${metinUrl}`, ikon: LinkedinLogoIcon },
    { ad: "X'te paylaş", href: `https://x.com/intent/post?url=${metinUrl}&text=${metinBaslik}`, ikon: XLogoIcon },
    { ad: "WhatsApp ile paylaş", href: `https://wa.me/?text=${metinBaslik}%20${metinUrl}`, ikon: WhatsappLogoIcon },
  ];

  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "BlogPosting",
      headline: yazi.baslik,
      description: yazi.seo?.aciklama || yazi.ozet,
      datePublished: yazi.yayin_tarihi,
      inLanguage: "tr-TR",
      mainEntityOfPage: { "@type": "WebPage", "@id": url },
      url,
      ...(kapakUrl ? { image: [kapakUrl] } : {}),
      author: { "@type": yazi.yazar_adi ? "Person" : "Organization", name: yazi.yazar_adi || site.ayarlar.firma_unvani },
      publisher: {
        "@type": "Organization",
        name: site.ayarlar.firma_unvani,
        logo: { "@type": "ImageObject", url: siteUrl("/brand/logo.svg") },
      },
      ...(yazi.kategori ? { articleSection: yazi.kategori.ad } : {}),
      ...(yazi.etiketler?.length ? { keywords: yazi.etiketler.join(", ") } : {}),
      ...(yazi.okuma_suresi ? { timeRequired: `PT${yazi.okuma_suresi}M` } : {}),
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Anasayfa", item: siteUrl("/") },
        { "@type": "ListItem", position: 2, name: "Blog", item: siteUrl("/blog") },
        { "@type": "ListItem", position: 3, name: yazi.baslik, item: url },
      ],
    },
  ];

  return (
    <>
      <JsonLd veri={jsonLd} />
      <SayfaUstu genislik="dar" altBosluk={yazi.kapak ? "pb-40 md:pb-48" : "pb-16 md:pb-20"}>
        <Reveal>
          <nav aria-label="Sayfa yolu" className="mb-8 text-sm text-white/60">
            <ol className="flex flex-wrap items-center gap-2">
              <li>
                <Link href="/" className="hover:text-white">
                  Anasayfa
                </Link>
              </li>
              <li aria-hidden>/</li>
              <li>
                <Link href="/blog" className="hover:text-white">
                  Blog
                </Link>
              </li>
              {yazi.kategori ? (
                <>
                  <li aria-hidden>/</li>
                  <li>
                    <Link href={`/blog?kategori=${yazi.kategori.slug}`} className="hover:text-white">
                      {yazi.kategori.ad}
                    </Link>
                  </li>
                </>
              ) : null}
            </ol>
          </nav>
          <h1 className="text-3xl leading-tight font-bold text-white sm:text-4xl lg:text-5xl">{yazi.baslik}</h1>
          {yazi.ozet ? <p className="mt-6 text-lg leading-relaxed text-white/70">{yazi.ozet}</p> : null}
          <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-white/60">
            {yazi.yazar_adi ? <span className="font-medium text-white/85">{yazi.yazar_adi}</span> : null}
            <time dateTime={yazi.yayin_tarihi}>{tarihFormatla(yazi.yayin_tarihi)}</time>
            {yazi.okuma_suresi ? <span>{yazi.okuma_suresi} dk okuma</span> : null}
          </div>
        </Reveal>
      </SayfaUstu>

      <Section arka_plan="acik" padding="yok" genislik="dar" className="pb-20 md:pb-28">
        {yazi.kapak ? (
          <div className="relative -mt-28 mb-12 aspect-[16/9] overflow-hidden rounded-panel border border-line bg-dark shadow-kart-hover md:-mt-36">
            <MediaImage medya={yazi.kapak} fill priority sizes="(min-width: 768px) 768px, 100vw" className="object-cover" />
          </div>
        ) : (
          <div className="pt-14" />
        )}

        <article
          className="prose-eisa mx-auto"
          // İçerik backend'de nh3 ile sanitize edilir (CONTRACT §5).
          dangerouslySetInnerHTML={{ __html: yazi.icerik_html || "" }}
        />

        {yazi.etiketler?.length ? (
          <ul aria-label="Etiketler" className="mt-12 flex flex-wrap gap-2">
            {yazi.etiketler.map((e) => (
              <li key={e} className="rounded-full bg-gri px-3 py-1 text-sm text-muted">
                #{e}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-10 flex flex-wrap items-center justify-between gap-6 border-t border-line pt-8">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-sm font-semibold text-ink transition-colors hover:text-primary-hover"
          >
            <ArrowLeftIcon aria-hidden weight="bold" className="size-4" />
            Tüm yazılar
          </Link>
          <div className="flex items-center gap-2">
            <span className="mr-1 text-sm text-muted">Paylaş:</span>
            {paylasim.map(({ ad, href, ikon: Ikon }) => (
              <a
                key={ad}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`${ad} (yeni sekmede açılır)`}
                className="inline-flex size-10 items-center justify-center rounded-full border border-line text-muted transition-colors hover:border-primary hover:text-primary-hover"
              >
                <Ikon aria-hidden size={18} />
              </a>
            ))}
            <a
              href={`mailto:?subject=${metinBaslik}&body=${metinUrl}`}
              aria-label="E-posta ile paylaş"
              className="inline-flex size-10 items-center justify-center rounded-full border border-line text-muted transition-colors hover:border-primary hover:text-primary-hover"
            >
              <EnvelopeSimpleIcon aria-hidden size={18} />
            </a>
            <BaglantiKopyala url={url} />
          </div>
        </div>
      </Section>

      {digerleri.length ? (
        <Section arka_plan="gri" aria-labelledby="ilgili-yazilar-baslik">
          <h2 id="ilgili-yazilar-baslik" className="mb-10 text-center text-3xl font-bold text-dark">
            {yazi.ilgili?.length ? "İlgili yazılar" : "Diğer yazılar"}
          </h2>
          <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {digerleri.map((y) => (
              <li key={y.slug}>
                <BlogKart yazi={y} />
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
    </>
  );
}
