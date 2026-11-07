/**
 * Genel yardımcılar — sunucu ve istemci tarafında kullanılabilir.
 */

import { clsx, type ClassValue } from "clsx";

/** Sınıf adlarını birleştirir (clsx). */
export function cn(...girdiler: ClassValue[]): string {
  return clsx(girdiler);
}

/**
 * `uzun_metin` alanını paragraflara böler (CONTRACT §5: çift satır sonu paragraf ayırır,
 * tek satır sonu korunur). Boş paragraflar atılır.
 */
export function paragraflaraBol(metin: string | null | undefined): string[] {
  if (!metin) return [];
  return metin
    .replace(/\r\n/g, "\n")
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/**
 * Başlığı vurgu alt-metnine göre parçalar. `vurgu` başlıkta geçmiyorsa tek parça döner.
 * Örn: ("Kurumsal İş Ortağı Olun", "İş Ortağı") → [{metin:"Kurumsal ", vurgu:false}, {metin:"İş Ortağı", vurgu:true}, {metin:" Olun", vurgu:false}]
 */
export function vurguParcala(
  baslik: string,
  vurgu?: string | null,
): Array<{ metin: string; vurgu: boolean }> {
  if (!vurgu || !baslik.includes(vurgu)) return [{ metin: baslik, vurgu: false }];
  const i = baslik.indexOf(vurgu);
  return [
    { metin: baslik.slice(0, i), vurgu: false },
    { metin: vurgu, vurgu: true },
    { metin: baslik.slice(i + vurgu.length), vurgu: false },
  ].filter((p) => p.metin.length > 0);
}

const sayiBicimi = new Intl.NumberFormat("tr-TR");

/** Sayıyı tr-TR biçiminde yazar: 185000 → "185.000" */
export function sayiFormatla(deger: number, secenekler?: Intl.NumberFormatOptions): string {
  return secenekler ? new Intl.NumberFormat("tr-TR", secenekler).format(deger) : sayiBicimi.format(deger);
}

/** Para tutarı: (185000, "TL") → "185.000 TL" */
export function paraFormatla(deger: number, paraBirimi = "TL"): string {
  return `${sayiBicimi.format(deger)} ${paraBirimi}`.trim();
}

/** ISO tarihi Türkçe uzun biçimde yazar: "7 Kasım 2026". Geçersizse boş string. */
export function tarihFormatla(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return "";
  return new Intl.DateTimeFormat("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Europe/Istanbul",
  }).format(t);
}

/* ------------------------------------------------------------------ */
/* Link sınıflandırma                                                  */
/* ------------------------------------------------------------------ */

/** `#x` veya `/#x`, `/sayfa#x` gibi anchor içeren iç link mi? */
export function anchorIceriyor(href: string): boolean {
  return href.startsWith("#") || (href.startsWith("/") && href.includes("#"));
}

/** Site içi yol mu? (`/` ile başlar, `//` ile başlamaz) */
export function icLinkMi(href: string): boolean {
  return href.startsWith("/") && !href.startsWith("//");
}

/** Dış link mi? (http/https veya protokol-göreli) */
export function disLinkMi(href: string): boolean {
  return /^https?:\/\//i.test(href) || href.startsWith("//");
}

/** mailto:/tel: gibi sayfa değiştirmeyen şema mı? */
export function semaLinkiMi(href: string): boolean {
  return /^(mailto|tel|sms):/i.test(href);
}

/**
 * href'i yol + hash olarak ayırır. `#x` → { yol: null, hash: "x" }, `/a#x` → { yol: "/a", hash: "x" }.
 */
export function hrefAyir(href: string): { yol: string | null; hash: string | null } {
  const i = href.indexOf("#");
  if (i === -1) return { yol: href || null, hash: null };
  const yol = href.slice(0, i) || null;
  const hash = decodeURIComponent(href.slice(i + 1)) || null;
  return { yol, hash };
}

/** Pathname'leri karşılaştırmak için normalize eder ("/a/" → "/a", "" → "/"). */
export function yolNormalize(yol: string | null | undefined): string {
  if (!yol) return "/";
  const temiz = yol.split("?")[0].replace(/\/+$/, "");
  return temiz === "" ? "/" : temiz;
}

/** Sayfa slug'ını URL yoluna çevirir: "anasayfa" → "/", "kvkk" → "/kvkk" */
export function slugYolu(slug: string): string {
  return slug === "anasayfa" ? "/" : `/${slug}`;
}
