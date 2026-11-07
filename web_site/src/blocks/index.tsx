/**
 * Blok kayıt defteri (registry) ve BlockRenderer.
 *
 * Tip → bileşen haritası. Yeni blok tipi eklemek için:
 *   1) CONTRACT §8 + src/lib/types.ts (XVeri + BlokVeriHaritasi)
 *   2) src/blocks/<tip-tireli>.tsx (default export)
 *   3) aşağıdaki BLOKLAR haritası (tip sistemi eksik anahtarı derleme hatası olarak yakalar)
 *
 * Kurallar (ayrıntı: src/blocks/README.md):
 * - BlockRenderer her bloğu `<div id={anchor_id} data-blok-tip=…>` ile sarar → anchor id'si
 *   HER ZAMAN bu sarmalayıcıdadır; bloklar kök elementlerine id vermez.
 * - Bilinmeyen tip / bozuk veri: blok atlanır, console.warn yazılır; sayfa çökmez.
 * - Sayfanın ilk bloğu koyu bir başlık bloğuysa (hero, sayfa_basligi) sarmalayıcıya
 *   `data-ilk-blok="koyu"` eklenir → header en üstte açık renk (şeffaf) modda başlar.
 */

import BasvuruFormu from "./basvuru-formu";
import BlogSonYazilar from "./blog-son-yazilar";
import CtaBanner from "./cta-banner";
import Ekip from "./ekip";
import GorselMetin from "./gorsel-metin";
import Hero from "./hero";
import KazancHesaplayici from "./kazanc-hesaplayici";
import LogoBandi from "./logo-bandi";
import OzellikKartlari from "./ozellik-kartlari";
import SayfaBasligi from "./sayfa-basligi";
import Sayaclar from "./sayaclar";
import ScrollHikaye from "./scroll-hikaye";
import Sss from "./sss";
import SurecAdimlari from "./surec-adimlari";
import VurguBandi from "./vurgu-bandi";
import ZenginMetin from "./zengin-metin";
import type { BilinmeyenBlok, Blok, BlokTipi, BlokVeriHaritasi } from "@/lib/types";
import type { BlokBileseni } from "./types";

export type { BlokProps, BlokBileseni } from "./types";

export const BLOKLAR: { [T in BlokTipi]: BlokBileseni<BlokVeriHaritasi[T]> } = {
  hero: Hero,
  sayfa_basligi: SayfaBasligi,
  ozellik_kartlari: OzellikKartlari,
  vurgu_bandi: VurguBandi,
  scroll_hikaye: ScrollHikaye,
  surec_adimlari: SurecAdimlari,
  gorsel_metin: GorselMetin,
  kazanc_hesaplayici: KazancHesaplayici,
  sayaclar: Sayaclar,
  logo_bandi: LogoBandi,
  sss: Sss,
  cta_banner: CtaBanner,
  basvuru_formu: BasvuruFormu,
  blog_son_yazilar: BlogSonYazilar,
  ekip: Ekip,
  zengin_metin: ZenginMetin,
};

/** İlk blok olduğunda header'ı koyu-üst (şeffaf, açık metin) moduna alan tipler. */
export const KOYU_UST_BLOKLAR: ReadonlySet<string> = new Set<BlokTipi>(["hero", "sayfa_basligi"]);

/** Sayfa bir koyu başlık bloğuyla mı başlıyor? */
export function koyuUstMu(bloklar: Array<Blok | BilinmeyenBlok>): boolean {
  const ilk = bloklar.find((b) => b && Object.prototype.hasOwnProperty.call(BLOKLAR, b.tip));
  return Boolean(ilk && KOYU_UST_BLOKLAR.has(ilk.tip));
}

function bilinenTipMi(tip: string): tip is BlokTipi {
  return Object.prototype.hasOwnProperty.call(BLOKLAR, tip);
}

/** Anchor id güvenliği: yalnızca [a-z0-9-_] (CMS zaten doğrular; savunma amaçlı). */
function guvenliAnchor(anchor: string | null | undefined): string | undefined {
  if (!anchor) return undefined;
  const temiz = anchor.trim();
  return /^[A-Za-z][\w-]*$/.test(temiz) ? temiz : undefined;
}

export interface BlockRendererProps {
  bloklar: Array<Blok | BilinmeyenBlok>;
  sayfaSlug: string;
}

export function BlockRenderer({ bloklar, sayfaSlug }: BlockRendererProps) {
  const gecerli = (bloklar ?? []).filter((b): b is Blok => {
    if (!b || typeof b !== "object") return false;
    if (!bilinenTipMi(b.tip)) {
      console.warn(`[e-isa blok] Bilinmeyen blok tipi atlandı: "${b.tip}" (sayfa: ${sayfaSlug}, id: ${b.id})`);
      return false;
    }
    if (!b.veri || typeof b.veri !== "object") {
      console.warn(`[e-isa blok] Verisi olmayan blok atlandı: ${b.tip} (sayfa: ${sayfaSlug}, id: ${b.id})`);
      return false;
    }
    return true;
  });

  return (
    <>
      {gecerli.map((blok, sira) => {
        const Bilesen = BLOKLAR[blok.tip] as BlokBileseni<unknown>;
        const anchorId = guvenliAnchor(blok.anchor_id);
        const ilk = sira === 0;
        return (
          <div
            key={blok.id || `${blok.tip}-${sira}`}
            id={anchorId}
            data-blok-tip={blok.tip}
            data-ilk-blok={ilk && KOYU_UST_BLOKLAR.has(blok.tip) ? "koyu" : undefined}
          >
            <Bilesen
              veri={blok.veri}
              blokId={blok.id || `blok-${sira}`}
              anchorId={anchorId}
              sira={sira}
              ilk={ilk}
              sayfaSlug={sayfaSlug}
            />
          </div>
        );
      })}
    </>
  );
}
