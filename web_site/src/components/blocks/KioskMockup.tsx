"use client";

/**
 * HTML/CSS ile çizilmiş dikey e-isa kiosku (24" Samsung tarzı). Dekoratiftir (aria-hidden);
 * anlatılan akış her zaman sayfa metninde de bulunur.
 *
 * Modlar:
 *  - "dongu"     (hero): soru → seçim → analiz → kategori önerisi → QR → eczacı onayı → başa.
 *                Ekran görünür değilken döngü durur.
 *  - "kontrollu" (scroll_hikaye): `adim` + `ekran` dışarıdan verilir, değiştikçe geçiş animasyonu oynar.
 * reduced-motion: döngü durur (öneri ekranı statik gösterilir), tilt kapalı.
 */

import { AnimatePresence, motion, useInView, useSpring } from "motion/react";
import { useEffect, useRef, useState, type PointerEvent } from "react";
import { Icon } from "@/components/ui/Icon";
import { EASE_EISA } from "@/lib/hareket";
import { useAzHareket, useInceIsaretci } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { KioskQr } from "./KioskQr";

/** Döngü ekranlarının süreleri (ms): soru, seçim, analiz, öneri, qr, onay */
const SURELER = [2400, 1500, 2000, 3000, 2600, 2600];
const STATIK_EKRAN = 3;

const SECENEKLER = [
  { ikon: "Lightning", metin: "Enerji" },
  { ikon: "Moon", metin: "Uyku" },
  { ikon: "ShieldCheck", metin: "Bağışıklık" },
  { ikon: "Leaf", metin: "Sindirim" },
] as const;

export interface KioskEkrani {
  baslik: string;
  metin: string;
}

export interface KioskMockupProps {
  mod?: "dongu" | "kontrollu";
  /** kontrollu: aktif adım (0'dan) */
  adim?: number;
  /** kontrollu: toplam adım */
  toplam?: number;
  /** kontrollu: ekranda gösterilecek içerik */
  ekran?: KioskEkrani;
  /** kontrollu: ekran ikonu (CONTRACT ikon adı) */
  ikon?: string;
  className?: string;
}

export function KioskMockup({ mod = "dongu", adim = 0, toplam = 1, ekran, ikon, className }: KioskMockupProps) {
  const kok = useRef<HTMLDivElement>(null);
  const gorunur = useInView(kok, { amount: 0.3 });
  const azHareket = useAzHareket();
  const inceIsaretci = useInceIsaretci();
  const tiltAktif = inceIsaretci && !azHareket;
  const [durum, setDurum] = useState(0);

  useEffect(() => {
    if (mod !== "dongu" || azHareket || !gorunur) return;
    const t = window.setTimeout(() => setDurum((d) => (d + 1) % SURELER.length), SURELER[durum]);
    return () => window.clearTimeout(t);
  }, [mod, azHareket, gorunur, durum]);

  const rx = useSpring(0, { stiffness: 120, damping: 16 });
  const ry = useSpring(0, { stiffness: 120, damping: 16 });
  const hareket = (e: PointerEvent<HTMLDivElement>) => {
    if (!tiltAktif) return;
    const r = e.currentTarget.getBoundingClientRect();
    ry.set(((e.clientX - r.left) / r.width - 0.5) * 12);
    rx.set(-((e.clientY - r.top) / r.height - 0.5) * 8);
  };
  const birak = () => {
    rx.set(0);
    ry.set(0);
  };

  const dongudeki = azHareket ? STATIK_EKRAN : durum;
  const anahtar = mod === "kontrollu" ? `k-${adim}` : dongudeki <= 1 ? "soru" : `d-${dongudeki}`;

  return (
    <div
      ref={kok}
      aria-hidden
      onPointerMove={hareket}
      onPointerLeave={birak}
      className={cn("relative mx-auto w-full max-w-[17.5rem] [perspective:1200px] sm:max-w-[18.5rem]", className)}
    >
      <motion.div style={tiltAktif ? { rotateX: rx, rotateY: ry } : undefined} className="relative [transform-style:preserve-3d]">
        <div className="absolute -inset-12 -z-10 rounded-full bg-primary/20 blur-3xl" />

        {/* Gövde */}
        <div className="relative rounded-[2.4rem] border border-white/10 bg-linear-to-b from-[#252d38] to-[#0d1117] p-2.5 shadow-koyu">
          <div className="absolute inset-x-0 top-[0.35rem] mx-auto h-1 w-10 rounded-full bg-white/10" />
          {/* Ekran */}
          <div className="relative aspect-[9/15.5] overflow-hidden rounded-[1.9rem] bg-[#f6f8f7]">
            <div className="flex items-center justify-between px-5 pt-4 pb-2">
              <span className="flex items-center gap-1.5 font-display text-[0.8rem] font-bold text-dark">
                <span className="size-2 rounded-full bg-primary" />
                e-isa
              </span>
              <span className="text-[0.62rem] font-medium tracking-wide text-muted">Eczane Asistanı</span>
            </div>

            <div className="relative h-[calc(100%-2.75rem)]">
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={anahtar}
                  initial={{ opacity: 0, y: 14, filter: "blur(4px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
                  transition={{ duration: azHareket ? 0 : 0.45, ease: EASE_EISA }}
                  className="absolute inset-0 flex flex-col px-4 pb-4"
                >
                  {mod === "kontrollu" ? (
                    <KontrolluEkran adim={adim} toplam={toplam} ekran={ekran} ikon={ikon} />
                  ) : (
                    <DonguEkrani durum={dongudeki} />
                  )}
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Cam parlaması */}
            <div className="pointer-events-none absolute inset-0 bg-linear-to-tr from-transparent via-transparent to-white/50 mix-blend-soft-light" />
          </div>
        </div>

        {/* Ayak */}
        <div className="mx-auto h-10 w-12 bg-linear-to-b from-[#1b222b] to-[#0f141a]" />
        <div className="mx-auto h-3 w-44 rounded-full bg-linear-to-b from-[#2a333f] to-[#0b0f14] shadow-koyu" />
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function DonguEkrani({ durum }: { durum: number }) {
  if (durum <= 1) {
    const secili = durum === 1;
    return (
      <>
        <p className="mt-2 text-[0.62rem] font-semibold tracking-[0.14em] text-primary-hover uppercase">Soru 1 / 3</p>
        <p className="mt-1.5 font-display text-[1.02rem] leading-snug font-bold text-dark">
          Bugünlerde en çok neye ihtiyaç duyuyorsunuz?
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          {SECENEKLER.map((s, i) => {
            const aktif = secili && i === 0;
            return (
              <div
                key={s.metin}
                className={cn(
                  "relative flex flex-col items-start gap-2 rounded-xl border p-3 transition-all duration-300",
                  aktif ? "scale-[1.03] border-primary bg-primary-soft shadow-cta" : "border-line bg-white",
                )}
              >
                <Icon ad={s.ikon} boyut={20} className={aktif ? "text-primary" : "text-brand-deep"} />
                <span className="text-[0.72rem] font-semibold text-ink">{s.metin}</span>
                {aktif ? (
                  <>
                    <span className="absolute top-2 right-2 size-3 rounded-full bg-primary" />
                    <span className="absolute top-2 right-2 size-3 animate-nabiz rounded-full bg-primary" />
                  </>
                ) : null}
              </div>
            );
          })}
        </div>
        <div className="mt-auto">
          <div className="mb-2 flex justify-between text-[0.6rem] text-muted">
            <span>2-4 kısa soru</span>
            <span>~60 sn</span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-line">
            <motion.div
              className="h-full rounded-full bg-primary"
              initial={{ width: "12%" }}
              animate={{ width: secili ? "33%" : "20%" }}
              transition={{ duration: 0.6, ease: EASE_EISA }}
            />
          </div>
        </div>
      </>
    );
  }

  if (durum === 2) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <div className="relative flex size-24 items-center justify-center">
          <svg viewBox="0 0 100 100" className="absolute inset-0 animate-yavas-don">
            <circle cx="50" cy="50" r="46" fill="none" stroke="#ed1c24" strokeOpacity="0.35" strokeWidth="2" strokeDasharray="6 8" />
          </svg>
          <span className="absolute inset-3 animate-nabiz rounded-full bg-primary/15" />
          <span className="relative flex size-14 items-center justify-center rounded-2xl bg-dark text-white shadow-koyu">
            <Icon ad="Brain" boyut={28} className="text-[#ff5a60]" />
          </span>
        </div>
        <p className="mt-5 font-display text-[0.95rem] font-bold text-dark">Yanıtlarınız değerlendiriliyor</p>
        <p className="mt-1 text-[0.68rem] text-muted">Bilimsel kategori mantığıyla eşleştiriliyor…</p>
        <div className="mt-5 h-1 w-3/4 overflow-hidden rounded-full bg-line">
          <motion.div
            className="h-full rounded-full bg-linear-to-r from-primary to-[#ff7a6b]"
            initial={{ width: "0%" }}
            animate={{ width: "100%" }}
            transition={{ duration: 1.7, ease: "easeInOut" }}
          />
        </div>
      </div>
    );
  }

  if (durum === 3) {
    return (
      <>
        <p className="mt-2 text-[0.62rem] font-semibold tracking-[0.14em] text-primary-hover uppercase">Kategori önerisi</p>
        <div className="mt-3 overflow-hidden rounded-2xl bg-linear-to-br from-primary to-[#b5121a] p-4 text-white shadow-cta">
          <Icon ad="Sparkle" boyut={22} className="text-white" />
          <p className="mt-2 font-display text-[1rem] leading-tight font-bold">Enerji & Vitamin Desteği</p>
          <p className="mt-1 text-[0.66rem] text-white/80">Marka değil, ihtiyaç kategorisi</p>
        </div>
        <div className="mt-3 space-y-2">
          {["Tamamlayıcı: Uyku düzeni", "Tamamlayıcı: Bağışıklık"].map((t, i) => (
            <motion.div
              key={t}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 + i * 0.15, duration: 0.4, ease: EASE_EISA }}
              className="flex items-center gap-2 rounded-xl border border-line bg-white px-3 py-2 text-[0.68rem] font-medium text-ink"
            >
              <Icon ad="CheckCircle" boyut={16} className="text-basari" />
              {t}
            </motion.div>
          ))}
        </div>
        <p className="mt-auto flex items-center gap-1.5 rounded-xl bg-dark px-3 py-2 text-[0.64rem] font-medium text-white/85">
          <Icon ad="ShieldCheck" boyut={14} className="text-[#ff5a60]" />
          Son karar her zaman eczacınızda
        </p>
      </>
    );
  }

  if (durum === 4) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <div className="relative rounded-2xl bg-white p-3 shadow-kart-hover ring-1 ring-line">
          <KioskQr className="size-28" />
          <motion.span
            className="absolute inset-x-3 h-0.5 rounded-full bg-primary/70 shadow-[0_0_12px_2px_rgba(237,28,36,0.5)]"
            initial={{ top: "12%" }}
            animate={{ top: ["12%", "88%", "12%"] }}
            transition={{ duration: 2.2, ease: "easeInOut", repeat: Infinity }}
          />
        </div>
        <p className="mt-5 font-display text-[0.95rem] font-bold text-dark">Fişinizi eczacınıza iletin</p>
        <p className="mt-1 text-[0.68rem] text-muted">QR kod ile öneri saniyeler içinde eczacı panelinde</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center text-center">
      <svg viewBox="0 0 64 64" className="size-20">
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
      <p className="mt-4 font-display text-[1rem] font-bold text-dark">Eczacı onayı</p>
      <p className="mt-1 px-2 text-[0.68rem] leading-relaxed text-muted">
        Öneri, eczacınızın mesleki uzmanlığıyla değerlendirilir.
      </p>
    </div>
  );
}

function KontrolluEkran({
  adim,
  toplam,
  ekran,
  ikon,
}: {
  adim: number;
  toplam: number;
  ekran?: KioskEkrani;
  ikon?: string;
}) {
  return (
    <>
      <p className="mt-2 text-[0.62rem] font-semibold tracking-[0.14em] text-primary-hover uppercase">
        Adım {adim + 1} / {toplam}
      </p>
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <div className="relative flex size-20 items-center justify-center">
          <span className="absolute inset-0 animate-nabiz rounded-3xl bg-primary/15" />
          <span className="relative flex size-16 items-center justify-center rounded-3xl bg-linear-to-br from-primary to-[#b5121a] text-white shadow-cta">
            <Icon ad={ikon} boyut={30} className="text-white" />
          </span>
        </div>
        <p className="mt-6 font-display text-[1.05rem] leading-snug font-bold text-dark">{ekran?.baslik}</p>
        {ekran?.metin ? <p className="mt-2 px-1 text-[0.72rem] leading-relaxed text-muted">{ekran.metin}</p> : null}
      </div>
      <div className="flex justify-center gap-1.5">
        {Array.from({ length: toplam }, (_, i) => (
          <span
            key={i}
            className={cn("h-1.5 rounded-full transition-all duration-500", i === adim ? "w-6 bg-primary" : "w-1.5 bg-line")}
          />
        ))}
      </div>
    </>
  );
}