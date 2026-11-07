/**
 * ekip — Ekip. CONTRACT §8.
 * Kişi kartları; foto yoksa baş harflerden gradyan halkalı avatar. Tek kişide geniş yatay kart.
 */

import { LinkedinLogoIcon } from "@phosphor-icons/react/dist/ssr/LinkedinLogo";
import { MediaImage } from "@/components/ui/MediaImage";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { EkipKisisi, EkipVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

function basHarfler(ad: string): string {
  return ad
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p.charAt(0).toLocaleUpperCase("tr-TR"))
    .join("");
}

function Avatar({ kisi, boyut }: { kisi: EkipKisisi; boyut: "normal" | "buyuk" }) {
  const buyuk = boyut === "buyuk";
  return (
    <div
      className={cn(
        "relative shrink-0 rounded-full bg-linear-to-br from-primary via-[#ff7a6b] to-brand-deep p-[3px] transition-transform duration-500 ease-eisa group-hover:scale-105",
        buyuk ? "size-36 md:size-44" : "size-28",
      )}
    >
      <div className="relative size-full overflow-hidden rounded-full bg-dark ring-4 ring-zemin-kart">
        <MediaImage medya={kisi.foto} fill sizes={buyuk ? "176px" : "112px"} className="object-cover">
          <span
            aria-hidden
            className={cn(
              "flex h-full items-center justify-center bg-linear-to-br from-dark to-dark-3 font-display font-bold text-white",
              buyuk ? "text-5xl" : "text-3xl",
            )}
          >
            {basHarfler(kisi.ad_soyad)}
          </span>
        </MediaImage>
      </div>
    </div>
  );
}

function Linkedin({ kisi }: { kisi: EkipKisisi }) {
  if (!kisi.linkedin) return null;
  return (
    <a
      href={kisi.linkedin}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${kisi.ad_soyad} LinkedIn profili (yeni sekmede açılır)`}
      className="inline-flex size-10 items-center justify-center rounded-full border border-zemin-cizgi text-zemin-soluk transition-all duration-300 hover:-translate-y-0.5 hover:border-primary hover:text-primary"
    >
      <LinkedinLogoIcon aria-hidden size={20} weight="duotone" />
    </a>
  );
}

export default function Ekip({ veri, blokId }: BlokProps<EkipVeri>) {
  const kisiler = (veri.kisiler ?? []).filter((k) => k?.ad_soyad);
  if (!kisiler.length) return null;
  const baslikId = `${blokId}-baslik`;
  const tek = kisiler.length === 1;

  return (
    <Section arka_plan="acik" aria-labelledby={baslikId}>
      <SectionHeading ust_baslik={veri.ust_baslik} baslik={veri.baslik} aciklama={veri.aciklama} baslikId={baslikId} />
      {tek ? (
        <Reveal className="mx-auto max-w-4xl">
          <article className="group relative flex flex-col items-center gap-8 overflow-hidden rounded-panel border border-zemin-cizgi bg-zemin-kart p-8 text-center shadow-kart md:flex-row md:items-center md:gap-10 md:p-12 md:text-left">
            <div aria-hidden className="absolute -top-24 -left-24 size-64 rounded-full bg-primary/10 blur-3xl" />
            <Avatar kisi={kisiler[0]} boyut="buyuk" />
            <div className="relative">
              <h3 className="font-display text-2xl font-bold text-zemin-baslik md:text-3xl">{kisiler[0].ad_soyad}</h3>
              <p className="mt-1 font-medium text-zemin-vurgu">{kisiler[0].unvan}</p>
              {kisiler[0].biyografi ? (
                <p className="mt-4 leading-relaxed text-zemin-soluk">{kisiler[0].biyografi}</p>
              ) : null}
              {kisiler[0].linkedin ? (
                <div className="mt-6">
                  <Linkedin kisi={kisiler[0]} />
                </div>
              ) : null}
            </div>
          </article>
        </Reveal>
      ) : (
        <Stagger as="ul" className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {kisiler.map((k, i) => (
            <StaggerItem
              as="li"
              key={i}
              className="group flex flex-col items-center rounded-kart border border-zemin-cizgi bg-zemin-kart p-8 text-center shadow-kart transition-[transform,box-shadow] duration-500 ease-eisa hover:-translate-y-1 hover:shadow-kart-hover"
            >
              <Avatar kisi={k} boyut="normal" />
              <h3 className="mt-6 font-display text-xl font-semibold text-zemin-baslik">{k.ad_soyad}</h3>
              <p className="mt-1 text-sm font-medium text-zemin-vurgu">{k.unvan}</p>
              {k.biyografi ? <p className="mt-4 text-sm leading-relaxed text-zemin-soluk">{k.biyografi}</p> : null}
              {k.linkedin ? (
                <div className="mt-auto pt-5">
                  <Linkedin kisi={k} />
                </div>
              ) : null}
            </StaggerItem>
          ))}
        </Stagger>
      )}
    </Section>
  );
}