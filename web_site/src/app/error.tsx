"use client";

/**
 * Segment hata sınırı. Ör. API'ye ulaşılamadığında (ApiHatasi) gösterilir.
 * ISR: daha önce üretilmiş sayfalar bu durumda son başarılı sürümle sunulmaya devam eder;
 * bu ekran yalnızca hiç önbelleği olmayan bir sayfa ilk kez üretilemediğinde görünür.
 */

import { useEffect } from "react";
import { ArrowClockwiseIcon } from "@phosphor-icons/react/dist/ssr/ArrowClockwise";
import { HataSahnesi } from "@/components/HataSahnesi";
import { ButonLink, butonSiniflari } from "@/components/ui/ButonLink";

export default function HataSayfasi({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error("[e-isa] sayfa hatası:", error);
  }, [error]);

  const kod = error instanceof Error && "digest" in error && typeof error.digest === "string" ? error.digest : null;

  return (
    <HataSahnesi
      kod="Hata"
      baslik="İçerik şu anda yüklenemedi"
      aciklama="Geçici bir bağlantı sorunu yaşıyoruz. Lütfen birkaç saniye sonra tekrar deneyin."
    >
      <button type="button" onClick={() => retry()} className={butonSiniflari("birincil")}>
        <ArrowClockwiseIcon aria-hidden weight="bold" className="size-4" />
        Tekrar dene
      </button>
      <ButonLink href="/" stil="ikincil">
        Anasayfa
      </ButonLink>
      {kod ? <p className="mt-6 w-full text-xs text-white/40">Hata kodu: {kod}</p> : null}
    </HataSahnesi>
  );
}
