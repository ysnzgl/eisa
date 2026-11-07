/**
 * On-demand revalidation webhook'u (CONTRACT §6).
 *
 *   POST /api/revalidate
 *   Header: X-Revalidate-Secret: <REVALIDATE_SECRET>
 *   Gövde:  { "tags": ["sayfa:anasayfa", "sayfalar", "site"] }
 *   Yanıt:  200 { "revalidated": [...] } | 401 (yanlış secret) | 400 (geçersiz gövde)
 *
 * Backend publish sonrası her pod'a ayrı ayrı çağırır (headless service fan-out).
 * `revalidateTag(tag, { expire: 0 })`: dış webhook için önerilen biçim — sonraki istek taze veriyle üretilir.
 */

import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";
import { env } from "@/lib/env";

/** İzinli tag biçimleri: site, sayfalar, blog, sayfa:<slug>, blog:<slug> */
const TAG_DESENI = /^(site|sayfalar|blog|sayfa:[a-z0-9-]+|blog:[a-z0-9-]+)$/;

function sirEsitMi(gelen: string, beklenen: string): boolean {
  const a = Buffer.from(gelen);
  const b = Buffer.from(beklenen);
  if (a.length !== b.length) {
    // Uzunluk sızdırmamak için yine de sabit süreli karşılaştırma yap.
    timingSafeEqual(b, b);
    return false;
  }
  return timingSafeEqual(a, b);
}

export async function POST(istek: Request) {
  const sir = istek.headers.get("x-revalidate-secret") ?? "";
  if (!sir || !sirEsitMi(sir, env.revalidateSecret)) {
    return Response.json({ hata: "Yetkisiz." }, { status: 401 });
  }

  let govde: unknown;
  try {
    govde = await istek.json();
  } catch {
    return Response.json({ hata: "Geçersiz JSON gövdesi." }, { status: 400 });
  }

  const tags = (govde as { tags?: unknown } | null)?.tags;
  if (!Array.isArray(tags)) {
    return Response.json({ hata: "`tags` dizisi zorunludur." }, { status: 400 });
  }

  const revalidated: string[] = [];
  const atlanan: string[] = [];
  for (const t of tags) {
    if (typeof t === "string" && t.length <= 256 && TAG_DESENI.test(t)) {
      revalidateTag(t, { expire: 0 });
      revalidated.push(t);
    } else {
      atlanan.push(String(t).slice(0, 100));
    }
  }

  if (atlanan.length) console.warn(`[e-isa revalidate] tanınmayan tag'ler atlandı: ${atlanan.join(", ")}`);
  console.info(`[e-isa revalidate] ${revalidated.join(", ") || "(yok)"}`);

  return Response.json({ revalidated, ...(atlanan.length ? { atlanan } : {}) });
}
