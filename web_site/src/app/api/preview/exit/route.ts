/**
 * Önizlemeden çıkış (CONTRACT §7): draft mode kapatılır, `eisa_preview` çerezi silinir.
 *
 *   GET|POST /api/preview/exit?yol=/sayfa
 *
 * `yol` yalnızca site içi bir yol ise kullanılır; aksi halde anasayfaya dönülür.
 */

import { cookies, draftMode } from "next/headers";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { ONIZLEME_CEREZI } from "@/lib/api";

function guvenliYol(yol: string | null): string {
  if (!yol || !yol.startsWith("/") || yol.startsWith("//") || yol.startsWith("/\\")) return "/";
  return yol.startsWith("/api/") ? "/" : yol;
}

async function cikis(istek: NextRequest) {
  (await draftMode()).disable();
  (await cookies()).delete(ONIZLEME_CEREZI);
  redirect(guvenliYol(istek.nextUrl.searchParams.get("yol")));
}

export async function GET(istek: NextRequest) {
  return cikis(istek);
}

export async function POST(istek: NextRequest) {
  return cikis(istek);
}
