/**
 * MOCK API — `MOCK_API=1` iken lib/api.ts bu fonksiyonları kullanır.
 * Yanıt biçimleri CONTRACT §3 ile birebir aynıdır.
 */

import type { BlogDetay, BlogListe, PageData, SayfaListeOgesi, SiteData } from "../types";
import { mockBlogYazilari, mockKategoriler, ozetle } from "./blog";
import { mockSayfalar } from "./sayfalar";
import { mockSite } from "./site";

export { mockSite };

/** Derin kopya — çağıran tarafın fixture'ı değiştirmesini engeller. */
function kopya<T>(v: T): T {
  return structuredClone(v);
}

export function mockSiteGetir(): SiteData {
  return kopya(mockSite);
}

export function mockSayfaListesi(): SayfaListeOgesi[] {
  return Object.values(mockSayfalar).map((s) => ({
    slug: s.slug,
    guncellenme: s.yayin_tarihi ?? "2026-11-07T10:00:00Z",
  }));
}

export function mockSayfaGetir(slug: string): PageData | null {
  const s = mockSayfalar[slug];
  return s ? kopya(s) : null;
}

export function mockBlogListe(params: { kategori?: string; sayfa?: number; boyut?: number }): BlogListe {
  const boyut = Math.min(Math.max(params.boyut ?? 9, 1), 24);
  const sirali = [...mockBlogYazilari].sort((a, b) => b.yayin_tarihi.localeCompare(a.yayin_tarihi));
  const filtreli = params.kategori ? sirali.filter((y) => y.kategori?.slug === params.kategori) : sirali;
  const sayfaSayisi = Math.max(1, Math.ceil(filtreli.length / boyut));
  const sayfa = Math.min(Math.max(params.sayfa ?? 1, 1), sayfaSayisi);
  const bas = (sayfa - 1) * boyut;
  return {
    sonuclar: filtreli.slice(bas, bas + boyut).map(ozetle),
    toplam: filtreli.length,
    sayfa,
    sayfa_sayisi: sayfaSayisi,
    kategoriler: kopya(mockKategoriler),
  };
}

export function mockBlogYazisi(slug: string): BlogDetay | null {
  const y = mockBlogYazilari.find((x) => x.slug === slug);
  if (!y) return null;
  const ilgili = mockBlogYazilari
    .filter((x) => x.slug !== slug && x.kategori?.slug && x.kategori.slug === y.kategori?.slug)
    .slice(0, 3)
    .map(ozetle);
  return { ...kopya(y), ilgili };
}
