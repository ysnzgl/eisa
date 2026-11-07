"use client";

/**
 * İstemci bileşenlerine site genel verisini sağlar (layout'ta sunucudan prop olarak gelir).
 *
 *   const { ayarlar } = useSite();          // iletişim bilgileri, sosyal linkler...
 *   const url = useMediaUrl()(medya.yol);   // MEDIA_BASE_URL + yol
 *
 * Sunucu bileşenlerinde bunun yerine `getSite()` ve `mediaUrl()` (lib/api.ts) kullanın.
 */

import { createContext, useCallback, useContext, type ReactNode } from "react";
import { mediaUrlOlustur } from "@/lib/media";
import type { SiteAyarlari } from "@/lib/types";

interface SiteBaglami {
  ayarlar: SiteAyarlari;
  mediaTabani: string;
  siteUrl: string;
}

const Baglam = createContext<SiteBaglami | null>(null);

export function SiteProvider({ deger, children }: { deger: SiteBaglami; children: ReactNode }) {
  return <Baglam.Provider value={deger}>{children}</Baglam.Provider>;
}

export function useSite(): SiteBaglami {
  const b = useContext(Baglam);
  if (!b) throw new Error("useSite() yalnızca <SiteProvider> içinde kullanılabilir.");
  return b;
}

/** `(yol) => tam URL | null` döndürür. */
export function useMediaUrl(): (yol: string | null | undefined) => string | null {
  const b = useContext(Baglam);
  const taban = b?.mediaTabani ?? "";
  return useCallback((yol: string | null | undefined) => mediaUrlOlustur(taban, yol), [taban]);
}
