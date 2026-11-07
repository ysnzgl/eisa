"use client";

/**
 * Başvuru formu istemci adacığı (basvuru_formu bloğu kullanır).
 * Gönderim: server action `basvuruGonder` (src/app/actions/basvuru.ts) — tarayıcıdan API'ye istek gitmez.
 * Alan adları CONTRACT ile birebir: tip, ad_soyad, kurum, eposta, telefon, il, mesaj, kvkk_onay,
 * kaynak_sayfa, website (honeypot).
 */

import { motion } from "motion/react";
import { usePathname } from "next/navigation";
import { startTransition, useActionState, useId, type FormEvent } from "react";
import { CircleNotchIcon } from "@phosphor-icons/react/dist/ssr/CircleNotch";
import { PaperPlaneTiltIcon } from "@phosphor-icons/react/dist/ssr/PaperPlaneTilt";
import { WarningCircleIcon } from "@phosphor-icons/react/dist/ssr/WarningCircle";
import { basvuruGonder } from "@/app/actions/basvuru";
import { butonSiniflari } from "@/components/ui/ButonLink";
import { EASE_EISA } from "@/lib/hareket";
import { ILLER } from "@/lib/iller";
import type { BasvuruSonucu, BasvuruTipi } from "@/lib/types";
import { cn } from "@/lib/utils";

const KURUM_ETIKETI: Record<BasvuruTipi, string> = {
  pilot: "Eczane adı",
  sponsor: "Firma / marka",
  genel: "Kurum",
};

const ALAN_SINIFI =
  "w-full rounded-xl border border-zemin-cizgi bg-white px-4 py-3 text-ink transition-[border-color,box-shadow] duration-200 placeholder:text-muted/70 hover:border-muted/40 focus:border-primary focus:shadow-[0_0_0_4px_rgb(237_28_36/0.12)] focus-visible:outline-none aria-invalid:border-primary";

export interface BasvuruFormIstemciProps {
  tip: BasvuruTipi;
  basariMesaji: string;
  kvkkHref: string;
  className?: string;
}

function Basarili({ mesaj }: { mesaj: string }) {
  return (
    <motion.div
      role="status"
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: EASE_EISA }}
      className="flex flex-col items-center px-4 py-10 text-center"
    >
      <svg viewBox="0 0 64 64" className="size-20" aria-hidden>
        <circle cx="32" cy="32" r="29" fill="none" stroke="#1f9d6b" strokeOpacity="0.15" strokeWidth="4" />
        <circle
          cx="32"
          cy="32"
          r="29"
          fill="none"
          stroke="#1f9d6b"
          strokeWidth="4"
          strokeLinecap="round"
          pathLength={1}
          className="ciz"
          transform="rotate(-90 32 32)"
        />
        <path
          d="M20 33 l8 8 l16 -18"
          fill="none"
          stroke="#1f9d6b"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={1}
          className="ciz [--gecikme:0.5s]"
        />
      </svg>
      <p className="mt-6 font-display text-2xl font-bold text-zemin-baslik">Teşekkürler!</p>
      <p className="mt-2 max-w-md leading-relaxed text-zemin-soluk">{mesaj || "Başvurunuz alındı. En kısa sürede sizinle iletişime geçeceğiz."}</p>
    </motion.div>
  );
}

export function BasvuruFormIstemci({ tip, basariMesaji, kvkkHref, className }: BasvuruFormIstemciProps) {
  const pathname = usePathname();
  const [sonuc, gonder, bekliyor] = useActionState<BasvuruSonucu | null, FormData>(basvuruGonder, null);
  const id = useId();
  const hata = (alan: string) => sonuc?.hatalar?.[alan]?.[0];

  if (sonuc?.ok) return <Basarili mesaj={basariMesaji} />;

  const etiket = (alanId: string, metin: string, zorunlu?: boolean) => (
    <label htmlFor={alanId} className="mb-1.5 block text-sm font-medium text-zemin-baslik">
      {metin}
      {zorunlu ? <span className="text-zemin-vurgu"> *</span> : null}
    </label>
  );

  const hataMetni = (alanId: string, ad: string) =>
    hata(ad) ? (
      <p id={`${alanId}-hata`} className="mt-1.5 flex items-center gap-1.5 text-sm text-zemin-vurgu">
        <WarningCircleIcon aria-hidden size={16} className="shrink-0" />
        {hata(ad)}
      </p>
    ) : null;

  const ortak = (ad: string) => {
    const alanId = `${id}-${ad}`;
    return {
      id: alanId,
      name: ad,
      "aria-invalid": hata(ad) ? true : undefined,
      "aria-describedby": hata(ad) ? `${alanId}-hata` : undefined,
      className: ALAN_SINIFI,
    };
  };

  const alan = (
    ad: string,
    metin: string,
    secenek: { zorunlu?: boolean; tur?: string; otomatik?: string; satir?: number; max?: number; yerTutucu?: string } = {},
  ) => {
    const alanId = `${id}-${ad}`;
    return (
      <div className={secenek.satir ? "sm:col-span-2" : undefined}>
        {etiket(alanId, metin, secenek.zorunlu)}
        {secenek.satir ? (
          <textarea
            rows={secenek.satir}
            required={secenek.zorunlu}
            maxLength={secenek.max}
            placeholder={secenek.yerTutucu}
            {...ortak(ad)}
            className={cn(ALAN_SINIFI, "resize-y")}
          />
        ) : (
          <input
            type={secenek.tur ?? "text"}
            required={secenek.zorunlu}
            maxLength={secenek.max}
            autoComplete={secenek.otomatik}
            placeholder={secenek.yerTutucu}
            {...ortak(ad)}
          />
        )}
        {hataMetni(alanId, ad)}
      </div>
    );
  };

  const ilId = `${id}-il`;
  const kvkkId = `${id}-kvkk_onay`;

  // JS açıkken gönderim onSubmit üzerinden yapılır: `<form action>` React 19'da gönderim
  // sonrası alanları sıfırlar; doğrulama hatasında kullanıcının yazdıkları kaybolmasın.
  // JS kapalıyken `action={gonder}` (progressive enhancement) çalışmaya devam eder.
  const gonderIstemci = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const veri = new FormData(e.currentTarget);
    startTransition(() => gonder(veri));
  };

  return (
    <form action={gonder} onSubmit={gonderIstemci} noValidate className={cn("relative grid gap-5 sm:grid-cols-2", className)}>
      <input type="hidden" name="tip" value={tip} />
      <input type="hidden" name="kaynak_sayfa" value={pathname || "/"} />
      {/* Honeypot: gerçek kullanıcılar görmez/doldurmaz */}
      <div aria-hidden className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Web siteniz
          <input type="text" name="website" tabIndex={-1} autoComplete="off" defaultValue="" />
        </label>
      </div>

      {alan("ad_soyad", "Ad soyad", { zorunlu: true, otomatik: "name", max: 150 })}
      {alan("kurum", KURUM_ETIKETI[tip], { otomatik: "organization", max: 200 })}
      {alan("eposta", "E-posta", { zorunlu: true, tur: "email", otomatik: "email", max: 254, yerTutucu: "ornek@eczane.com" })}
      {alan("telefon", "Telefon", { tur: "tel", otomatik: "tel", max: 20, yerTutucu: "05xx xxx xx xx" })}

      <div className="sm:col-span-2">
        {etiket(ilId, "İl")}
        <select {...ortak("il")} defaultValue="" autoComplete="address-level1">
          <option value="">Seçiniz</option>
          {ILLER.map((il) => (
            <option key={il} value={il}>
              {il}
            </option>
          ))}
        </select>
        {hataMetni(ilId, "il")}
      </div>

      {alan("mesaj", "Mesajınız", { satir: 4, max: 2000, yerTutucu: "Kısaca ihtiyacınızdan bahsedin…" })}

      <div className="sm:col-span-2">
        <div className="flex items-start gap-3">
          <input
            id={kvkkId}
            type="checkbox"
            name="kvkk_onay"
            required
            aria-invalid={hata("kvkk_onay") ? true : undefined}
            aria-describedby={hata("kvkk_onay") ? `${kvkkId}-hata` : undefined}
            className="mt-1 size-4 shrink-0 accent-primary"
          />
          <label htmlFor={kvkkId} className="text-sm leading-relaxed text-zemin-soluk">
            <a href={kvkkHref} target="_blank" rel="noopener noreferrer" className="font-medium text-zemin-vurgu underline underline-offset-4">
              KVKK Aydınlatma Metni
            </a>
            &apos;ni okudum; başvurum kapsamında kişisel verilerimin işlenmesini anladım. <span className="text-zemin-vurgu">*</span>
          </label>
        </div>
        {hataMetni(kvkkId, "kvkk_onay")}
      </div>

      {sonuc && !sonuc.ok && sonuc.mesaj ? (
        <p role="alert" className="flex items-start gap-2 rounded-xl bg-primary-soft px-4 py-3 text-sm text-primary-hover sm:col-span-2">
          <WarningCircleIcon aria-hidden size={18} className="mt-0.5 shrink-0" />
          {sonuc.mesaj}
        </p>
      ) : null}

      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={bekliyor}
          className={butonSiniflari("birincil", "buyuk", "w-full disabled:cursor-wait disabled:opacity-70 sm:w-auto")}
        >
          {bekliyor ? (
            <>
              <CircleNotchIcon aria-hidden weight="bold" className="size-5 animate-spin" />
              Gönderiliyor…
            </>
          ) : (
            <>
              Başvuruyu gönder
              <PaperPlaneTiltIcon aria-hidden weight="bold" className="size-5 transition-transform duration-300 group-hover/buton:translate-x-0.5 group-hover/buton:-translate-y-0.5" />
            </>
          )}
        </button>
      </div>
    </form>
  );
}