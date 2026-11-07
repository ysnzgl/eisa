import type { MetadataRoute } from "next";
import { getBlogListe, getSayfaListesi, siteUrl } from "@/lib/api";
import type { BlogOzet } from "@/lib/types";
import { slugYolu } from "@/lib/utils";

/**
 * sitemap.xml — yayındaki CMS sayfaları + blog yazıları.
 * Backend'e ulaşılamazsa en azından anasayfa ve blog döner (build kırılmaz); 1 saat sonra yenilenir.
 */

export const revalidate = 3600;

const MAKS_BLOG_SAYFASI = 20; // 20 × 24 = 480 yazı

async function tumBlogYazilari(): Promise<BlogOzet[]> {
  const ilk = await getBlogListe({ boyut: 24, sayfa: 1 });
  const yazilar = [...ilk.sonuclar];
  const son = Math.min(ilk.sayfa_sayisi, MAKS_BLOG_SAYFASI);
  for (let s = 2; s <= son; s++) {
    const l = await getBlogListe({ boyut: 24, sayfa: s });
    yazilar.push(...l.sonuclar);
  }
  return yazilar;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const girdiler: MetadataRoute.Sitemap = [];

  try {
    const sayfalar = await getSayfaListesi();
    for (const s of sayfalar) {
      girdiler.push({
        url: siteUrl(slugYolu(s.slug)),
        lastModified: s.guncellenme ? new Date(s.guncellenme) : undefined,
        changeFrequency: s.slug === "anasayfa" ? "weekly" : "monthly",
        priority: s.slug === "anasayfa" ? 1 : 0.7,
      });
    }
  } catch (hata) {
    console.warn("[e-isa sitemap] sayfa listesi alınamadı:", hata instanceof Error ? hata.message : hata);
  }

  if (!girdiler.some((g) => g.url === siteUrl("/"))) {
    girdiler.unshift({ url: siteUrl("/"), changeFrequency: "weekly", priority: 1 });
  }

  girdiler.push({ url: siteUrl("/blog"), changeFrequency: "weekly", priority: 0.6 });

  try {
    for (const y of await tumBlogYazilari()) {
      girdiler.push({
        url: siteUrl(`/blog/${y.slug}`),
        lastModified: y.yayin_tarihi ? new Date(y.yayin_tarihi) : undefined,
        changeFrequency: "monthly",
        priority: 0.5,
      });
    }
  } catch (hata) {
    console.warn("[e-isa sitemap] blog listesi alınamadı:", hata instanceof Error ? hata.message : hata);
  }

  return girdiler;
}
