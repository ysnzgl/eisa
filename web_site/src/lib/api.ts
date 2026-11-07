import "server-only";

/**
 * e-isa site — sunucu tarafı veri katmanı (CONTRACT §3, §4, §6, §7).
 *
 * Kurallar:
 * - Tüm istekler `API_INTERNAL_URL` üzerinden, sunucuda yapılır (tarayıcıdan API'ye istek gitmez).
 * - Önbellek: klasik `fetch(..., { next: { tags, revalidate } })` modeli (cacheComponents KAPALI).
 *   Tag'ler CONTRACT §6: `site`, `sayfalar`, `sayfa:<slug>`, `blog`, `blog:<slug>`.
 *   Süreler: sayfa/site 3600 sn, blog listesi 300 sn (zamanlanmış yazılar için).
 * - Draft mode açıksa sayfa/blog detayı preview uçlarından `cache: 'no-store'` ile okunur;
 *   token httpOnly `eisa_preview` çerezindedir.
 * - Dayanıklılık:
 *     getSite()          → hata olursa seed içerikli yedek veri döner (site asla çökmez).
 *     getSayfa()/getBlogYazisi() → 404 ise `null` (çağıran notFound() yapar); ağ/5xx hatasında
 *                          `ApiHatasi` fırlatır → error.tsx; ISR son başarılı sürümü sunmaya devam eder.
 *     getSayfaListesi()/getBlogListe() → hata fırlatır; generateStaticParams/sitemap yakalar.
 *     getSonYazilar()    → hata olursa [] döner (blok kendini gizler).
 * - MOCK_API=1 iken hiçbir ağ isteği yapılmaz; src/lib/mock fixture'ları döner.
 */

import { cache } from "react";
import { cookies, draftMode } from "next/headers";
import { unstable_rethrow } from "next/navigation";
import { env } from "./env";
import { mediaUrlOlustur } from "./media";
import {
  mockBlogListe,
  mockBlogYazisi,
  mockSayfaGetir,
  mockSayfaListesi,
  mockSiteGetir,
} from "./mock";
import type {
  BlogDetay,
  BlogListe,
  BlogOzet,
  MediaRef,
  PageData,
  SayfaListeOgesi,
  SiteAyarlari,
  SiteData,
} from "./types";

/* ------------------------------------------------------------------ */
/* Sabitler                                                            */
/* ------------------------------------------------------------------ */

/** Önizleme token'ının saklandığı httpOnly çerez (CONTRACT §7). */
export const ONIZLEME_CEREZI = "eisa_preview";

/** Zaman bazlı revalidate süreleri (sn). Route segment `revalidate` export'ları da bunlarla uyumlu tutulur. */
export const REVALIDATE = {
  site: 3600,
  sayfa: 3600,
  sayfaListesi: 3600,
  blogListe: 300,
  blogDetay: 3600,
} as const;

/** Cache tag'leri (CONTRACT §6). */
export const TAG = {
  site: "site",
  sayfalar: "sayfalar",
  sayfa: (slug: string) => `sayfa:${slug}`,
  blog: "blog",
  blogYazisi: (slug: string) => `blog:${slug}`,
} as const;

/** CMS slug biçimi (CONTRACT §5: `^[a-z0-9-]+$`). URL'den gelen slug API'ye gitmeden doğrulanır. */
export const SLUG_DESENI = /^[a-z0-9-]+$/;

const PUBLIC = "/api/website/public";
const PREVIEW = "/api/website/preview";
const ISTEK_ZAMAN_ASIMI_MS = 8000;

/* ------------------------------------------------------------------ */
/* Hata ve düşük seviye istek                                          */
/* ------------------------------------------------------------------ */

export class ApiHatasi extends Error {
  /** HTTP durumu; ağ hatasında `null`. */
  readonly durum: number | null;
  readonly yol: string;

  constructor(mesaj: string, durum: number | null, yol: string) {
    super(mesaj);
    this.name = "ApiHatasi";
    this.durum = durum;
    this.yol = yol;
  }
}

interface IstekSecenekleri {
  tags?: string[];
  revalidate?: number;
  /** Önizleme: önbelleği tamamen atla. */
  noStore?: boolean;
}

interface IstekSonucu<T> {
  durum: number;
  /** 2xx ise gövde; 404/403 ise null. */
  veri: T | null;
}

/**
 * API'ye GET isteği. 404 ve 403 `veri: null` ile döner; diğer hatalar `ApiHatasi` fırlatır.
 * `yol` sorgu dizgesi dahil, `/api/...` ile başlar.
 */
async function apiGet<T>(yol: string, secenekler: IstekSecenekleri = {}): Promise<IstekSonucu<T>> {
  const url = `${env.apiInternalUrl}${yol}`;
  let yanit: Response;
  try {
    yanit = await fetch(url, {
      // App-key: public/önizleme uçları yalnızca site sunucusuna açıktır (yoksa API 404 döner).
      headers: { Accept: "application/json", "X-Website-Token": env.websiteServerToken },
      signal: AbortSignal.timeout(ISTEK_ZAMAN_ASIMI_MS),
      ...(secenekler.noStore
        ? { cache: "no-store" as const }
        : { next: { tags: secenekler.tags, revalidate: secenekler.revalidate } }),
    });
  } catch (hata) {
    unstable_rethrow(hata);
    const neden = hata instanceof Error ? hata.message : String(hata);
    throw new ApiHatasi(`API'ye ulaşılamadı (${yol}): ${neden}`, null, yol);
  }

  if (yanit.status === 404 || yanit.status === 403) {
    return { durum: yanit.status, veri: null };
  }
  if (!yanit.ok) {
    throw new ApiHatasi(`API hatası ${yanit.status} (${yol})`, yanit.status, yol);
  }
  try {
    return { durum: yanit.status, veri: (await yanit.json()) as T };
  } catch {
    throw new ApiHatasi(`API geçersiz JSON döndürdü (${yol})`, yanit.status, yol);
  }
}

/** Hata kaydı — sunucu loglarında tek biçim. */
function logla(baglam: string, hata: unknown): void {
  const mesaj = hata instanceof Error ? hata.message : String(hata);
  console.error(`[e-isa api] ${baglam}: ${mesaj}`);
}

/* ------------------------------------------------------------------ */
/* Önizleme (draft mode)                                               */
/* ------------------------------------------------------------------ */

/** Draft mode açık mı? Request scope dışında (ör. generateStaticParams) false döner. */
export async function onizlemeAcikMi(): Promise<boolean> {
  try {
    return (await draftMode()).isEnabled;
  } catch (hata) {
    unstable_rethrow(hata);
    return false;
  }
}

/** Draft mode açıksa `eisa_preview` çerezindeki token; değilse null. */
async function onizlemeTokeni(): Promise<string | null> {
  if (!(await onizlemeAcikMi())) return null;
  try {
    return (await cookies()).get(ONIZLEME_CEREZI)?.value ?? null;
  } catch (hata) {
    unstable_rethrow(hata);
    return null;
  }
}

/**
 * Önizleme token'ını backend preview ucunda doğrular (api/preview route'u kullanır).
 * Geçerliyse true. MOCK modunda içerik varsa her token geçerlidir.
 */
export async function onizlemeTokeniDogrula(tur: "sayfa" | "blog", slug: string, token: string): Promise<boolean> {
  if (!SLUG_DESENI.test(slug) || !token) return false;
  if (env.mockApi) return tur === "sayfa" ? mockSayfaGetir(slug) !== null : mockBlogYazisi(slug) !== null;
  const yol =
    tur === "sayfa"
      ? `${PREVIEW}/sayfalar/${slug}/?token=${encodeURIComponent(token)}`
      : `${PREVIEW}/blog/${slug}/?token=${encodeURIComponent(token)}`;
  try {
    const r = await apiGet<unknown>(yol, { noStore: true });
    return r.durum >= 200 && r.durum < 300;
  } catch (hata) {
    unstable_rethrow(hata);
    logla("önizleme doğrulama", hata);
    return false;
  }
}

/* ------------------------------------------------------------------ */
/* Site                                                                */
/* ------------------------------------------------------------------ */

/**
 * Site ayarları + menüler. ASLA hata fırlatmaz: API'ye ulaşılamazsa seed içerikli yedek döner
 * (build sırasında backend kapalı olsa bile layout render edilebilir).
 */
export const getSite = cache(async (): Promise<SiteData> => {
  if (env.mockApi) return mockSiteGetir();
  try {
    const r = await apiGet<SiteData>(`${PUBLIC}/site/`, { tags: [TAG.site], revalidate: REVALIDATE.site });
    if (r.veri) return r.veri;
    logla("site", new Error(`beklenmeyen durum ${r.durum}`));
  } catch (hata) {
    unstable_rethrow(hata);
    logla("site (yedek veri kullanılıyor)", hata);
  }
  return mockSiteGetir();
});

/* ------------------------------------------------------------------ */
/* Sayfalar                                                            */
/* ------------------------------------------------------------------ */

/** Yayındaki sayfaların listesi (sitemap, generateStaticParams). Hata fırlatabilir. */
export async function getSayfaListesi(): Promise<SayfaListeOgesi[]> {
  if (env.mockApi) return mockSayfaListesi();
  const r = await apiGet<SayfaListeOgesi[]>(`${PUBLIC}/sayfalar/`, {
    tags: [TAG.sayfalar],
    revalidate: REVALIDATE.sayfaListesi,
  });
  return r.veri ?? [];
}

/**
 * Sayfa detayı. Draft mode'da preview ucundan (no-store) okunur; token geçersizse (403)
 * yayındaki sürüme düşer. Bulunamazsa `null` → çağıran `notFound()` yapmalı.
 * Ağ/5xx hatasında `ApiHatasi` fırlatır.
 */
export const getSayfa = cache(async (slug: string): Promise<PageData | null> => {
  if (!SLUG_DESENI.test(slug)) return null;
  if (env.mockApi) return mockSayfaGetir(slug);

  const token = await onizlemeTokeni();
  if (token) {
    const r = await apiGet<PageData>(`${PREVIEW}/sayfalar/${slug}/?token=${encodeURIComponent(token)}`, {
      noStore: true,
    });
    if (r.durum !== 403) return r.veri;
    console.warn(`[e-isa api] önizleme token'ı geçersiz/süresi dolmuş (sayfa:${slug}); yayındaki sürüm gösteriliyor.`);
  }

  const r = await apiGet<PageData>(`${PUBLIC}/sayfalar/${slug}/`, {
    tags: [TAG.sayfa(slug)],
    revalidate: REVALIDATE.sayfa,
  });
  return r.veri;
});

/* ------------------------------------------------------------------ */
/* Blog                                                                */
/* ------------------------------------------------------------------ */

export interface BlogListeParametreleri {
  kategori?: string;
  sayfa?: number;
  /** En fazla 24 (CONTRACT §3). Varsayılan 9. */
  boyut?: number;
}

/** Blog listesi (300 sn revalidate + `blog` tag'i). Hata fırlatabilir. */
export const getBlogListe = cache(async (params: BlogListeParametreleri = {}): Promise<BlogListe> => {
  const kategori = params.kategori && SLUG_DESENI.test(params.kategori) ? params.kategori : undefined;
  const sayfa = Math.max(1, Math.floor(params.sayfa ?? 1));
  const boyut = Math.min(Math.max(1, Math.floor(params.boyut ?? 9)), 24);

  if (env.mockApi) return mockBlogListe({ kategori, sayfa, boyut });

  const qs = new URLSearchParams();
  if (kategori) qs.set("kategori", kategori);
  qs.set("sayfa", String(sayfa));
  qs.set("boyut", String(boyut));
  const r = await apiGet<BlogListe>(`${PUBLIC}/blog/?${qs.toString()}`, {
    tags: [TAG.blog],
    revalidate: REVALIDATE.blogListe,
  });
  // Geçersiz sayfa numarası vb. durumlarda backend 404 dönebilir: boş liste.
  return r.veri ?? { sonuclar: [], toplam: 0, sayfa, sayfa_sayisi: 1, kategoriler: [] };
});

/**
 * Son yazılar (ör. `blog_son_yazilar` bloğu). ASLA hata fırlatmaz; hata olursa [] döner.
 */
export async function getSonYazilar(adet = 3, kategori?: string): Promise<BlogOzet[]> {
  try {
    const liste = await getBlogListe({ boyut: Math.min(Math.max(adet, 1), 6), kategori: kategori || undefined });
    return liste.sonuclar;
  } catch (hata) {
    unstable_rethrow(hata);
    logla("son yazılar", hata);
    return [];
  }
}

/**
 * Blog yazısı detayı. Draft mode'da preview ucundan okunur. Bulunamazsa `null`.
 * Ağ/5xx hatasında `ApiHatasi` fırlatır.
 */
export const getBlogYazisi = cache(async (slug: string): Promise<BlogDetay | null> => {
  if (!SLUG_DESENI.test(slug)) return null;
  if (env.mockApi) return mockBlogYazisi(slug);

  const token = await onizlemeTokeni();
  if (token) {
    const r = await apiGet<BlogDetay>(`${PREVIEW}/blog/${slug}/?token=${encodeURIComponent(token)}`, {
      noStore: true,
    });
    if (r.durum !== 403) return r.veri;
    console.warn(`[e-isa api] önizleme token'ı geçersiz/süresi dolmuş (blog:${slug}); yayındaki sürüm gösteriliyor.`);
  }

  const r = await apiGet<BlogDetay>(`${PUBLIC}/blog/${slug}/`, {
    tags: [TAG.blog, TAG.blogYazisi(slug)],
    revalidate: REVALIDATE.blogDetay,
  });
  return r.veri;
});

/* ------------------------------------------------------------------ */
/* Medya / URL                                                         */
/* ------------------------------------------------------------------ */

/** `MEDIA_BASE_URL + yol`. İstemci bileşenlerinde `useMediaUrl()` kullanın. */
export function mediaUrl(yol: string | null | undefined): string | null {
  return mediaUrlOlustur(env.mediaBaseUrl, yol);
}

/** Site içi yolu mutlak URL'ye çevirir: "/blog" → "https://eisa.com.tr/blog" */
export function siteUrl(yol = "/"): string {
  return `${env.siteUrl}${yol.startsWith("/") ? "" : "/"}${yol}`;
}

/**
 * generateMetadata için Open Graph görselleri. Öncelik: içeriğin kendi görseli → site ayarlarındaki
 * og_gorsel → markalı varsayılan (/opengraph-image). Sayfa `openGraph` tanımladığında kök
 * opengraph-image miras alınmadığı için her zaman açıkça verilmelidir.
 */
export function ogGorselleri(
  medya: MediaRef | null | undefined,
  ayarlar: Pick<SiteAyarlari, "og_gorsel">,
  alt: string,
): Array<{ url: string; width?: number; height?: number; alt: string }> {
  const m = medya ?? ayarlar.og_gorsel;
  const url = m ? mediaUrl(m.yol) : null;
  if (m && url) {
    return [{ url, width: m.genislik ?? undefined, height: m.yukseklik ?? undefined, alt: m.alt || alt }];
  }
  return [{ url: "/opengraph-image", width: 1200, height: 630, alt }];
}
