"use client";

/**
 * Önizleme (draft mode) bandı — yalnızca draft mode açıkken layout tarafından render edilir.
 * "Çık" butonu GET formu ile /api/preview/exit'e gider (form prefetch edilmez → çerez yanlışlıkla silinmez).
 */

import { usePathname } from "next/navigation";
import { EyeIcon } from "@phosphor-icons/react/dist/ssr/Eye";

export function PreviewBanner() {
  const pathname = usePathname();
  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-[70] flex h-(--onizleme-bant) items-center justify-center gap-3 bg-primary-aa px-4 text-sm font-medium text-white"
    >
      <EyeIcon aria-hidden size={18} weight="bold" />
      <span>Önizleme modu — yayınlanmamış taslak içerik gösteriliyor.</span>
      <form method="GET" action="/api/preview/exit">
        <input type="hidden" name="yol" value={pathname || "/"} />
        <button
          type="submit"
          className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-primary-hover transition-colors hover:bg-white/90"
        >
          Çık
        </button>
      </form>
    </div>
  );
}
