/**
 * Önizleme girişi (CONTRACT §7).
 *
 *   GET /api/preview?tur=sayfa|blog&slug=<slug>&token=<imzalı token>
 *
 * Token backend preview ucunda doğrulanır; geçerliyse draft mode açılır, token httpOnly
 * `eisa_preview` çerezine yazılır ve ilgili sayfaya yönlendirilir. Yönlendirme hedefi
 * yalnızca doğrulanmış slug'dan üretilir (open redirect yok).
 */

import { cookies, draftMode } from "next/headers";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { ONIZLEME_CEREZI, onizlemeTokeniDogrula, SLUG_DESENI } from "@/lib/api";
import { env } from "@/lib/env";
import { slugYolu } from "@/lib/utils";

function hata(mesaj: string, durum: number) {
  return new Response(mesaj, { status: durum, headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" } });
}

export async function GET(istek: NextRequest) {
  const p = istek.nextUrl.searchParams;
  const tur = p.get("tur") ?? "sayfa";
  const slug = p.get("slug") ?? "";
  const token = p.get("token") ?? "";

  if ((tur !== "sayfa" && tur !== "blog") || !SLUG_DESENI.test(slug) || !token) {
    return hata("Geçersiz önizleme isteği.", 400);
  }

  const gecerli = await onizlemeTokeniDogrula(tur, slug, token);
  if (!gecerli) {
    return hata("Önizleme bağlantısı geçersiz veya süresi dolmuş. Portaldan yeniden önizleme açın.", 401);
  }

  (await draftMode()).enable();
  (await cookies()).set(ONIZLEME_CEREZI, token, {
    httpOnly: true,
    secure: env.siteUrl.startsWith("https://"),
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60, // token 1 saat geçerli (CONTRACT §4)
  });

  redirect(tur === "blog" ? `/blog/${slug}` : slugYolu(slug));
}
