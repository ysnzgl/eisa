/**
 * Blok bileşen sözleşmesi — ayrıntılar için src/blocks/README.md.
 */

import type { ReactNode } from "react";

export interface BlokProps<V> {
  /** CONTRACT §8 `veri` (tip güvenli). Opsiyonel alanlar boş string/undefined olabilir. */
  veri: V;
  /** Kalıcı blok anahtarı (ör. "b_42"). Benzersiz DOM id üretmek için: `${blokId}-baslik`. */
  blokId: string;
  /**
   * Blok anchor'ı (boşsa undefined). BİLGİ AMAÇLIDIR: `id` niteliği BlockRenderer'ın
   * sarmalayıcısına zaten verilmiştir — blok kendi kök elementine bu id'yi VERMEMELİ.
   */
  anchorId?: string;
  /** Sayfadaki sıra (0'dan). */
  sira: number;
  /** Sayfanın ilk bloğu mu? (hero/sayfa_basligi için LCP: görsellerde priority) */
  ilk: boolean;
  /** Bloğun bulunduğu sayfanın slug'ı (ör. "anasayfa"). */
  sayfaSlug: string;
}

/** Blok bileşeni: senkron veya async (server component) olabilir. */
export type BlokBileseni<V> = (props: BlokProps<V>) => ReactNode | Promise<ReactNode>;
