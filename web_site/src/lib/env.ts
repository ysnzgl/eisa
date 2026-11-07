import "server-only";

/**
 * Sunucu tarafı ortam değişkenleri (CONTRACT §1). Hepsinin lokal varsayılanı vardır.
 * İstemci bileşenlerinde KULLANMAYIN — istemciye gereken değerler (ör. medya tabanı)
 * layout'ta `SiteProvider` ile prop olarak aktarılır.
 */

function sonEgikCizgisiz(deger: string): string {
  return deger.replace(/\/+$/, "");
}

function bayrak(deger: string | undefined): boolean {
  return deger === "1" || deger?.toLowerCase() === "true";
}

export const env = {
  /** Sunucu tarafı fetch tabanı (K8s'te cluster içi servis adresi). */
  apiInternalUrl: sonEgikCizgisiz(process.env.API_INTERNAL_URL || "http://localhost:8000"),
  /** Medya `yol` alanının önüne eklenir (prod: https://api.eisa.com.tr). */
  mediaBaseUrl: sonEgikCizgisiz(process.env.MEDIA_BASE_URL || "http://localhost:8000"),
  /** Canonical, sitemap, OG için (prod: https://eisa.com.tr). */
  siteUrl: sonEgikCizgisiz(process.env.SITE_URL || "http://localhost:3000"),
  /** Backend → site revalidate webhook'u için ortak sır. */
  revalidateSecret: process.env.REVALIDATE_SECRET || "dev-revalidate-secret",
  /** Site sunucusunun API'ye "ben siteyim" demesi için (X-Website-Token). */
  websiteServerToken: process.env.WEBSITE_SERVER_TOKEN || "dev-website-token",
  /** MOCK_API=1 iken API yerine src/lib/mock fixture'ları kullanılır. */
  mockApi: bayrak(process.env.MOCK_API),
} as const;
