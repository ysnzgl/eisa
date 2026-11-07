"use server";

/**
 * Başvuru formu server action'ı (CONTRACT §3 `POST basvurular/`).
 *
 * Tarayıcı API'ye doğrudan istek atmaz; form bu action üzerinden sunucudan iletilir.
 * Gerçek istemci IP'si `X-Website-Client-IP` ile, site kimliği `X-Website-Token` ile gönderilir.
 *
 * Kullanım (client component):
 *   const [sonuc, gonder, bekliyor] = useActionState(basvuruGonder, null);
 *   <form action={gonder}> ... <input name="tip" type="hidden" value="pilot" /> ... </form>
 *
 * Form alan adları CONTRACT ile birebir: tip, ad_soyad, kurum, eposta, telefon, il, mesaj,
 * kvkk_onay (checkbox), kaynak_sayfa (hidden), website (honeypot — görünmez bırakın).
 */

import { headers } from "next/headers";
import { env } from "@/lib/env";
import type { BasvuruIstegi, BasvuruSonucu, BasvuruTipi } from "@/lib/types";

const TIPLER: BasvuruTipi[] = ["pilot", "sponsor", "genel"];
const EPOSTA_DESENI = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const GENEL_HATA =
  "Başvurunuz şu anda iletilemedi. Lütfen biraz sonra tekrar deneyin veya bize e-posta ile ulaşın.";

function metin(fd: FormData, ad: string, max = 500): string {
  const v = fd.get(ad);
  return typeof v === "string" ? v.trim().slice(0, max) : "";
}

function onayMi(fd: FormData, ad: string): boolean {
  const v = fd.get(ad);
  return v === "on" || v === "true" || v === "1";
}

/** Gelen istekten istemci IP'si (proxy arkasında x-forwarded-for'un ilk öğesi). */
async function istemciIp(): Promise<string> {
  const h = await headers();
  const xff = h.get("x-forwarded-for");
  const aday = (xff ? xff.split(",")[0] : h.get("x-real-ip") || "").trim();
  return /^[0-9a-fA-F:.]{3,45}$/.test(aday) ? aday : "";
}

/** İstemci tarafı ile aynı temel doğrulama (asıl doğrulama backend'dedir). */
function dogrula(g: BasvuruIstegi): Record<string, string[]> {
  const h: Record<string, string[]> = {};
  if (!g.ad_soyad) h.ad_soyad = ["Ad soyad zorunludur."];
  if (!g.eposta) h.eposta = ["E-posta zorunludur."];
  else if (!EPOSTA_DESENI.test(g.eposta)) h.eposta = ["Geçerli bir e-posta adresi girin."];
  if (g.telefon.length > 20) h.telefon = ["Telefon en fazla 20 karakter olabilir."];
  if (g.mesaj.length > 2000) h.mesaj = ["Mesaj en fazla 2000 karakter olabilir."];
  if (!g.kvkk_onay) h.kvkk_onay = ["Devam etmek için KVKK aydınlatma metnini onaylamanız gerekir."];
  return h;
}

/** DRF hata gövdesini `{ alan: [mesaj] }` biçimine normalize eder. */
function hatalariNormalize(govde: unknown): { hatalar: Record<string, string[]>; genel: string | null } {
  const hatalar: Record<string, string[]> = {};
  let genel: string | null = null;
  if (govde && typeof govde === "object" && !Array.isArray(govde)) {
    for (const [alan, deger] of Object.entries(govde as Record<string, unknown>)) {
      const mesajlar = (Array.isArray(deger) ? deger : [deger]).filter((m) => typeof m === "string") as string[];
      if (!mesajlar.length) continue;
      if (alan === "non_field_errors" || alan === "detail") genel = mesajlar.join(" ");
      else hatalar[alan] = mesajlar;
    }
  }
  return { hatalar, genel };
}

export async function basvuruGonder(_onceki: BasvuruSonucu | null, formData: FormData): Promise<BasvuruSonucu> {
  const tipHam = metin(formData, "tip", 20) as BasvuruTipi;
  const kaynak = metin(formData, "kaynak_sayfa", 200);

  const govde: BasvuruIstegi = {
    tip: TIPLER.includes(tipHam) ? tipHam : "genel",
    ad_soyad: metin(formData, "ad_soyad", 150),
    kurum: metin(formData, "kurum", 200),
    eposta: metin(formData, "eposta", 254),
    telefon: metin(formData, "telefon", 40),
    il: metin(formData, "il", 100),
    mesaj: metin(formData, "mesaj", 4000),
    kvkk_onay: onayMi(formData, "kvkk_onay"),
    kaynak_sayfa: kaynak.startsWith("/") ? kaynak : "/",
    website: metin(formData, "website", 200),
  };

  const hatalar = dogrula(govde);
  if (Object.keys(hatalar).length) {
    return { ok: false, hatalar, mesaj: "Lütfen işaretli alanları kontrol edin." };
  }

  if (env.mockApi) {
    return { ok: true, hatalar: {}, mesaj: "Başvurunuz alındı (MOCK modu — kayıt oluşturulmadı)." };
  }

  let yanit: Response;
  try {
    yanit = await fetch(`${env.apiInternalUrl}/api/website/public/basvurular/`, {
      method: "POST",
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Website-Token": env.websiteServerToken,
        "X-Website-Client-IP": await istemciIp(),
      },
      body: JSON.stringify(govde),
    });
  } catch (hata) {
    console.error("[e-isa basvuru] API'ye ulaşılamadı:", hata instanceof Error ? hata.message : hata);
    return { ok: false, hatalar: {}, mesaj: GENEL_HATA };
  }

  if (yanit.status === 201 || yanit.ok) {
    return { ok: true, hatalar: {}, mesaj: "Başvurunuz alındı." };
  }

  if (yanit.status === 429) {
    return {
      ok: false,
      hatalar: {},
      mesaj: "Kısa süre içinde çok fazla başvuru gönderildi. Lütfen bir süre sonra tekrar deneyin.",
    };
  }

  if (yanit.status === 400) {
    let govdeJson: unknown = null;
    try {
      govdeJson = await yanit.json();
    } catch {
      // gövde yoksa genel mesaj
    }
    const { hatalar: apiHatalari, genel } = hatalariNormalize(govdeJson);
    return {
      ok: false,
      hatalar: apiHatalari,
      mesaj: genel ?? "Lütfen işaretli alanları kontrol edin.",
    };
  }

  console.error(`[e-isa basvuru] beklenmeyen API yanıtı: ${yanit.status}`);
  return { ok: false, hatalar: {}, mesaj: GENEL_HATA };
}
