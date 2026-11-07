/**
 * Medya URL yardımcıları — hem sunucu hem istemci tarafında güvenle kullanılabilir (env okumaz).
 * Sunucuda `mediaUrl()` (lib/api.ts), istemcide `useMediaUrl()` (components/SiteProvider.tsx) kullanın.
 */

import type { MediaRef } from "./types";

/** `taban + yol` birleştirir. `yol` zaten mutlak URL ise olduğu gibi döner. Boşsa `null`. */
export function mediaUrlOlustur(taban: string, yol: string | null | undefined): string | null {
  if (!yol) return null;
  if (/^https?:\/\//i.test(yol)) return yol;
  const t = taban.replace(/\/+$/, "");
  return `${t}${yol.startsWith("/") ? "" : "/"}${yol}`;
}

/** MediaRef geçerli bir görsel mi? (null / boş yol → false) */
export function medyaVarMi(m: MediaRef | null | undefined): m is MediaRef {
  return Boolean(m && m.yol);
}
