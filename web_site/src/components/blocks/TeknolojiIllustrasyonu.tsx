/**
 * gorsel_metin bloğunda görsel yokken çizilen dekoratif illüstrasyon (aria-hidden, server component).
 * Koyu panel + ızgara + kiosk silueti + akan veri çizgileri + yüzen bilgi kartları.
 */

import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";

const KARTLAR = [
  { ikon: "Brain", metin: "Kategori eşleşmesi", sinif: "top-[12%] left-[6%]", gecikme: "0s" },
  { ikon: "CloudArrowUp", metin: "Bulut senkronizasyon", sinif: "top-[44%] right-[5%]", gecikme: "-2s" },
  { ikon: "QrCode", metin: "QR ile aktarım", sinif: "bottom-[10%] left-[10%]", gecikme: "-4s" },
];

export function TeknolojiIllustrasyonu({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      data-zemin="koyu"
      className={cn("relative isolate aspect-[4/3.3] w-full overflow-hidden rounded-panel bg-dark shadow-koyu", className)}
    >
      <div className="doku-izgara absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_80%)]" />
      <div className="absolute top-1/2 left-1/2 size-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/25 blur-3xl" />

      {/* Akan veri çizgileri */}
      <svg viewBox="0 0 400 330" className="absolute inset-0 h-full w-full" fill="none" preserveAspectRatio="none">
        {[
          "M60 70 C 140 70, 150 165, 200 165",
          "M350 170 C 290 170, 260 165, 200 165",
          "M80 280 C 150 280, 160 165, 200 165",
        ].map((d, i) => (
          <g key={i}>
            <path d={d} stroke="rgb(255 255 255 / 0.12)" strokeWidth="1.5" />
            <path
              d={d}
              pathLength={1}
              stroke="#ff5a60"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray="0.22 0.78"
              className="animate-akis"
              style={{ animationDelay: `${i * -1.1}s` }}
            />
          </g>
        ))}
      </svg>

      {/* Kiosk silueti */}
      <div className="absolute top-1/2 left-1/2 w-[22%] -translate-x-1/2 -translate-y-1/2">
        <div className="rounded-[1.1rem] border border-white/15 bg-linear-to-b from-[#252d38] to-[#0d1117] p-1.5 shadow-koyu">
          <div className="flex aspect-[9/15] flex-col gap-1.5 rounded-[0.8rem] bg-[#f6f8f7] p-2">
            <span className="h-1.5 w-1/3 rounded-full bg-primary" />
            <span className="h-1.5 w-3/4 rounded-full bg-dark/70" />
            <span className="h-1.5 w-1/2 rounded-full bg-dark/30" />
            <span className="mt-1 grid flex-1 grid-cols-2 gap-1">
              <span className="rounded-md bg-primary/15" />
              <span className="rounded-md bg-dark/10" />
              <span className="rounded-md bg-dark/10" />
              <span className="rounded-md bg-dark/10" />
            </span>
          </div>
        </div>
        <div className="mx-auto h-4 w-4 bg-[#141a21]" />
        <div className="mx-auto h-1.5 w-3/4 rounded-full bg-[#1f2731]" />
      </div>

      {KARTLAR.map((k) => (
        <div
          key={k.metin}
          style={{ animationDelay: k.gecikme }}
          className={cn(
            "cam-koyu absolute flex animate-yuzme items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-[0.7rem] font-semibold text-white shadow-koyu sm:text-xs",
            k.sinif,
          )}
        >
          <Icon ad={k.ikon} boyut={16} className="text-[#ff5a60]" />
          {k.metin}
        </div>
      ))}
    </div>
  );
}