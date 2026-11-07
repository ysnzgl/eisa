import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, Space_Grotesk } from "next/font/google";
import { CookieBanner } from "@/components/CookieBanner";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { JsonLd } from "@/components/JsonLd";
import { PreviewBanner } from "@/components/PreviewBanner";
import { SiteProvider } from "@/components/SiteProvider";
import { SmoothScroll } from "@/components/SmoothScroll";
import { getSite, ogGorselleri, onizlemeAcikMi } from "@/lib/api";
import { env } from "@/lib/env";
import { cn } from "@/lib/utils";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin", "latin-ext"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#0b0f14",
  colorScheme: "light",
};

export async function generateMetadata(): Promise<Metadata> {
  const { ayarlar } = await getSite();
  const siteAdi = ayarlar.site_adi || "e-isa";
  const sablon = ayarlar.seo_baslik_sablonu?.includes("%s") ? ayarlar.seo_baslik_sablonu : `%s | ${siteAdi}`;
  const gorseller = ogGorselleri(null, ayarlar, siteAdi);

  return {
    metadataBase: new URL(env.siteUrl),
    title: { default: siteAdi, template: sablon },
    description: ayarlar.seo_aciklama || undefined,
    applicationName: siteAdi,
    authors: [{ name: ayarlar.firma_unvani }],
    publisher: ayarlar.firma_unvani,
    formatDetection: { telephone: false, email: false, address: false },
    openGraph: {
      type: "website",
      locale: "tr_TR",
      siteName: siteAdi,
      images: gorseller,
    },
    twitter: { card: "summary_large_image", images: gorseller.map((g) => g.url) },
    robots: { index: true, follow: true },
  };
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const [site, onizleme] = await Promise.all([getSite(), onizlemeAcikMi()]);
  const { ayarlar, menuler } = site;

  const cerezPolitikasi =
    menuler.footer_alt.find((m) => m.href.includes("cerez"))?.href ?? "/cerez-politikasi";

  const organizasyon = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${env.siteUrl}/#organizasyon`,
    name: ayarlar.firma_unvani,
    alternateName: ayarlar.site_adi,
    url: env.siteUrl,
    logo: `${env.siteUrl}/brand/logo.svg`,
    ...(ayarlar.seo_aciklama ? { description: ayarlar.seo_aciklama } : {}),
    ...(ayarlar.eposta ? { email: ayarlar.eposta } : {}),
    ...(ayarlar.telefon ? { telephone: ayarlar.telefon } : {}),
    ...(ayarlar.adres ? { address: { "@type": "PostalAddress", streetAddress: ayarlar.adres, addressCountry: "TR" } } : {}),
    sameAs: ayarlar.sosyal_linkler.map((s) => s.url).filter(Boolean),
  };
  const webSitesi = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${env.siteUrl}/#website`,
    name: ayarlar.site_adi,
    url: env.siteUrl,
    inLanguage: "tr-TR",
    publisher: { "@id": `${env.siteUrl}/#organizasyon` },
  };

  return (
    <html lang="tr" className={cn(spaceGrotesk.variable, inter.variable, onizleme && "onizleme")}>
      <body>
        <a
          href="#icerik"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[80] focus:rounded-full focus:bg-white focus:px-5 focus:py-3 focus:font-semibold focus:text-ink focus:shadow-kart-hover"
        >
          İçeriğe geç
        </a>
        {onizleme ? <PreviewBanner /> : null}
        <SiteProvider deger={{ ayarlar, mediaTabani: env.mediaBaseUrl, siteUrl: env.siteUrl }}>
          <SmoothScroll />
          <Header
            menu={menuler.header}
            ayarlar={{ site_adi: ayarlar.site_adi, eposta: ayarlar.eposta, sosyal_linkler: ayarlar.sosyal_linkler }}
          />
          <main id="icerik" tabIndex={-1} className="min-h-[60vh] outline-none">
            {children}
          </main>
          <Footer site={site} />
          <CookieBanner politikaHref={cerezPolitikasi} />
        </SiteProvider>
        <JsonLd veri={[organizasyon, webSitesi]} />
      </body>
    </html>
  );
}
