"use client";

/**
 * kazanc_hesaplayici istemci kısmı: kaydırıcı → kademe → akan metrikler (+ opsiyonel tablo).
 * Kademe kuralı (CONTRACT §8): `etkilesim_min <= v <= etkilesim_max` olan İLK kademe;
 * v tüm kademelerin üstündeyse son kademe.
 */

import { animate } from "motion/react";
import { useEffect, useId, useRef, useState } from "react";
import { InfoIcon } from "@phosphor-icons/react/dist/ssr/Info";
import { GradientBackdrop } from "@/components/ui/Dekor";
import { EASE_EISA } from "@/lib/hareket";
import { useAzHareket } from "@/lib/hooks";
import type { KazancHesaplayiciVeri, KazancKademesi } from "@/lib/types";
import { cn, paraFormatla, sayiFormatla } from "@/lib/utils";

function kademeSec(kademeler: KazancKademesi[], v: number): KazancKademesi | undefined {
  return kademeler.find((k) => k.etkilesim_min <= v && v <= k.etkilesim_max) ?? (v > 0 ? kademeler.at(-1) : kademeler[0]);
}

function AkanSayi({ deger }: { deger: number }) {
  const azHareket = useAzHareket();
  const [gosterilen, setGosterilen] = useState(deger);
  const anlik = useRef(deger);

  useEffect(() => {
    if (azHareket) return;
    const kontrol = animate(anlik.current, deger, {
      duration: 0.6,
      ease: EASE_EISA,
      onUpdate: (v) => {
        anlik.current = v;
        setGosterilen(v);
      },
    });
    return () => kontrol.stop();
  }, [deger, azHareket]);

  return <span className="tabular-nums">{sayiFormatla(Math.round(azHareket ? deger : gosterilen))}</span>;
}

export function KazancIstemci({ veri }: { veri: KazancHesaplayiciVeri }) {
  const id = useId();
  const kademeler = (veri.kademeler ?? []).filter((k) => Number.isFinite(k.etkilesim_min) && Number.isFinite(k.etkilesim_max));
  const pb = veri.para_birimi || "TL";
  const enAz = Math.max(1, Math.min(...kademeler.map((k) => k.etkilesim_min), 1));
  const enCok = Math.max(Number(veri.slider_max) || 0, ...kademeler.map((k) => k.etkilesim_max), enAz + 1);
  const baslangic = Math.min(enCok, Math.max(enAz, Number(veri.varsayilan_etkilesim) || enAz));
  const [deger, setDeger] = useState(baslangic);

  if (!kademeler.length) return null;

  const kademe = kademeSec(kademeler, deger) ?? kademeler[0];
  const aktifSira = kademeler.indexOf(kademe);
  const dolu = ((deger - enAz) / (enCok - enAz)) * 100;

  const metrikler = [
    { etiket: "Günlük satış", deger: kademe.gunluk_satis, birim: "adet" },
    { etiket: "Aylık satış", deger: kademe.aylik_satis, birim: "adet" },
    { etiket: "Aylık ciro potansiyeli", deger: kademe.aylik_ciro, birim: pb },
    { etiket: "Aylık kâr potansiyeli", deger: kademe.aylik_kar, birim: pb, vurgulu: true },
  ];

  return (
    <>
      <div
        data-zemin="koyu"
        className="relative isolate overflow-hidden rounded-panel bg-dark p-6 text-zemin-metin shadow-koyu sm:p-10 lg:p-12"
      >
        <GradientBackdrop varyant="koyu" izgara />
        <div className="grid gap-10 lg:grid-cols-12 lg:gap-12">
          <div className="lg:col-span-5">
            <label htmlFor={`${id}-kaydirici`} className="eyebrow text-zemin-vurgu">
              Günlük etkileşim
            </label>
            <p className="mt-3 flex items-baseline gap-3">
              <span className="font-display text-6xl font-bold text-white tabular-nums sm:text-7xl">{deger}</span>
              <span className="text-white/60">kişi / gün</span>
            </p>
            <input
              id={`${id}-kaydirici`}
              type="range"
              min={enAz}
              max={enCok}
              step={1}
              value={deger}
              onChange={(e) => setDeger(Number(e.target.value))}
              aria-valuetext={`Günde ${deger} etkileşim`}
              className="kaydirici mt-8 w-full"
              style={{ "--dolu": `${dolu}%` } as React.CSSProperties}
            />
            <div className="mt-3 flex justify-between text-xs text-white/50">
              <span>{enAz}</span>
              <span>{enCok}</span>
            </div>

            <div className="mt-8 flex gap-1.5" role="group" aria-label="Etkileşim kademeleri">
              {kademeler.map((k, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setDeger(Math.round((k.etkilesim_min + k.etkilesim_max) / 2))}
                  aria-label={`${k.etkilesim_min}-${k.etkilesim_max} günlük etkileşim kademesini seç`}
                  aria-pressed={i === aktifSira}
                  className={cn(
                    "h-2 flex-1 rounded-full transition-colors duration-300",
                    i === aktifSira ? "bg-primary" : i < aktifSira ? "bg-primary/40" : "bg-white/12 hover:bg-white/25",
                  )}
                />
              ))}
            </div>
            <p className="mt-3 text-sm text-white/60">
              Kademe:{" "}
              <strong className="font-semibold text-white">
                {kademe.etkilesim_min}-{kademe.etkilesim_max}
              </strong>{" "}
              günlük etkileşim
            </p>
          </div>

          <div className="lg:col-span-7">
            <dl className="grid grid-cols-2 gap-3 sm:gap-4">
              {metrikler.map((m) => (
                <div
                  key={m.etiket}
                  className={cn(
                    "rounded-2xl border p-4 transition-colors duration-500 sm:p-6",
                    m.vurgulu ? "border-primary/40 bg-primary/10" : "border-white/10 bg-white/[0.04]",
                  )}
                >
                  <dt className="text-xs text-white/60 sm:text-sm">{m.etiket}</dt>
                  <dd className="mt-2 font-display text-2xl font-bold text-white sm:text-3xl">
                    <AkanSayi deger={m.deger} />
                    <span className="ml-1.5 text-sm font-medium text-white/55 sm:text-base">{m.birim}</span>
                  </dd>
                </div>
              ))}
            </dl>
            {veri.uyari_notu ? (
              <p className="mt-6 flex gap-2.5 text-sm leading-relaxed text-white/60">
                <InfoIcon aria-hidden size={18} weight="duotone" className="mt-0.5 shrink-0 text-[#ff5a60]" />
                {veri.uyari_notu}
              </p>
            ) : null}
            <p className="sr-only" aria-live="polite">
              {`Günde ${deger} etkileşimde aylık ciro potansiyeli ${paraFormatla(kademe.aylik_ciro, pb)}, kâr potansiyeli ${paraFormatla(kademe.aylik_kar, pb)}.`}
            </p>
          </div>
        </div>
      </div>

      {veri.tablo_goster ? (
        <div className="mt-8 overflow-x-auto rounded-kart border border-zemin-cizgi bg-zemin-kart shadow-kart">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <caption className="sr-only">Örnek etkileşim ve satış potansiyeli tablosu</caption>
            <thead className="bg-gri text-zemin-baslik">
              <tr>
                <th scope="col" className="p-4 font-semibold">Günlük etkileşim</th>
                <th scope="col" className="p-4 text-right font-semibold">Günlük satış</th>
                <th scope="col" className="p-4 text-right font-semibold">Aylık satış</th>
                <th scope="col" className="p-4 text-right font-semibold">Aylık ciro</th>
                <th scope="col" className="p-4 text-right font-semibold">Aylık kâr potansiyeli</th>
              </tr>
            </thead>
            <tbody>
              {kademeler.map((k, i) => (
                <tr
                  key={i}
                  className={cn(
                    "border-t border-zemin-cizgi transition-colors duration-300",
                    i === aktifSira && "bg-primary-soft",
                  )}
                >
                  <th scope="row" className="p-4 font-medium text-zemin-baslik">
                    {k.etkilesim_min}-{k.etkilesim_max}
                  </th>
                  <td className="p-4 text-right tabular-nums">{sayiFormatla(k.gunluk_satis)}</td>
                  <td className="p-4 text-right tabular-nums">{sayiFormatla(k.aylik_satis)}</td>
                  <td className="p-4 text-right tabular-nums">{paraFormatla(k.aylik_ciro, pb)}</td>
                  <td className="p-4 text-right font-semibold text-zemin-vurgu tabular-nums">{paraFormatla(k.aylik_kar, pb)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}