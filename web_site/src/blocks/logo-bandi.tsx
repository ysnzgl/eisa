/**
 * logo_bandi — Logo Bandı. CONTRACT §8.
 * Logolar sonsuz kayan bant (hover'da durur, kenarlar solar); logo yoksa davet kartı.
 */

import type { CSSProperties } from "react";
import { Icon } from "@/components/ui/Icon";
import { MediaImage } from "@/components/ui/MediaImage";
import { Reveal } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import type { LogoBandiVeri, LogoOgesi } from "@/lib/types";
import type { BlokProps } from "./types";

function LogoKutusu({ logo, kopya }: { logo: LogoOgesi; kopya: boolean }) {
  const gorsel = (
    <span className="relative block h-12 w-36">
      <MediaImage medya={logo.gorsel} alt={kopya ? "" : logo.ad} fill sizes="144px" className="object-contain" />
    </span>
  );
  return (
    <li
      aria-hidden={kopya || undefined}
      className="shrink-0 opacity-60 grayscale transition duration-300 hover:opacity-100 hover:grayscale-0"
    >
      {logo.url ? (
        <a
          href={logo.url}
          target="_blank"
          rel="noopener noreferrer"
          tabIndex={kopya ? -1 : undefined}
          aria-label={kopya ? undefined : `${logo.ad} (yeni sekmede açılır)`}
        >
          {gorsel}
        </a>
      ) : (
        gorsel
      )}
    </li>
  );
}

export default function LogoBandi({ veri, blokId }: BlokProps<LogoBandiVeri>) {
  const logolar = (veri.logolar ?? []).filter((l) => l?.gorsel);
  const baslikId = `${blokId}-baslik`;

  return (
    <Section arka_plan="acik" padding="kucuk" aria-labelledby={veri.baslik ? baslikId : undefined}>
      {veri.baslik ? (
        <h2 id={baslikId} className="eyebrow mb-10 text-center text-zemin-soluk">
          {veri.baslik}
        </h2>
      ) : null}

      {logolar.length ? (
        <div className="group relative overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
          <ul
            className="flex w-max animate-marquee items-center gap-16 group-hover:[animation-play-state:paused]"
            style={{ "--marquee-sure": `${Math.max(20, logolar.length * 5)}s` } as CSSProperties}
          >
            {logolar.map((l, i) => (
              <LogoKutusu key={`a-${i}`} logo={l} kopya={false} />
            ))}
            {logolar.map((l, i) => (
              <LogoKutusu key={`b-${i}`} logo={l} kopya />
            ))}
          </ul>
        </div>
      ) : (
        <Reveal className="mx-auto max-w-3xl">
          <div className="relative overflow-hidden rounded-panel border border-dashed border-zemin-cizgi bg-zemin-kart px-6 py-12 text-center shadow-kart sm:px-12">
            <div aria-hidden className="absolute -top-20 left-1/2 size-56 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
            <span className="relative mx-auto flex size-14 items-center justify-center rounded-2xl bg-primary-soft text-primary">
              <Icon ad="Handshake" boyut={30} />
            </span>
            <p className="relative mt-5 font-display text-2xl font-bold text-zemin-baslik">
              {veri.bos_mesaj || "Ekosisteme ilk katılan siz olun"}
            </p>
            <ul aria-hidden className="relative mt-8 grid grid-cols-3 gap-3 sm:grid-cols-6">
              {Array.from({ length: 6 }, (_, i) => (
                <li
                  key={i}
                  style={{ animationDelay: `${i * 0.3}s` }}
                  className="h-12 animate-parilti rounded-xl border border-dashed border-zemin-cizgi bg-gri/60"
                />
              ))}
            </ul>
          </div>
        </Reveal>
      )}
    </Section>
  );
}