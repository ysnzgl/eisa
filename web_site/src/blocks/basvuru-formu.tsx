/**
 * basvuru_formu — Başvuru Formu. CONTRACT §8.
 * Solda başlık + fayda maddeleri + iletişim bilgileri, sağda form kartı.
 * Form mantığı: _parcalar/BasvuruFormIstemci.tsx (server action: src/app/actions/basvuru.ts)
 */

import { EnvelopeSimpleIcon } from "@phosphor-icons/react/dist/ssr/EnvelopeSimple";
import { MapPinIcon } from "@phosphor-icons/react/dist/ssr/MapPin";
import { PhoneIcon } from "@phosphor-icons/react/dist/ssr/Phone";
import { WhatsappLogoIcon } from "@phosphor-icons/react/dist/ssr/WhatsappLogo";
import { Icon } from "@/components/ui/Icon";
import { Reveal, Stagger, StaggerItem } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { getSite } from "@/lib/api";
import type { BasvuruFormuVeri } from "@/lib/types";
import { slugYolu } from "@/lib/utils";
import { BasvuruFormIstemci } from "./_parcalar/BasvuruFormIstemci";
import type { BlokProps } from "./types";

export default async function BasvuruFormu({ veri, blokId }: BlokProps<BasvuruFormuVeri>) {
  const baslikId = `${blokId}-baslik`;
  const { ayarlar } = await getSite();
  const kvkkHref = slugYolu(veri.kvkk_sayfa_slug || "kvkk");
  const whatsapp = ayarlar.whatsapp?.replace(/[^\d]/g, "");

  const iletisim = veri.iletisim_bilgisi_goster
    ? [
        ayarlar.eposta && { ikon: EnvelopeSimpleIcon, etiket: ayarlar.eposta, href: `mailto:${ayarlar.eposta}` },
        ayarlar.telefon && {
          ikon: PhoneIcon,
          etiket: ayarlar.telefon,
          href: `tel:${ayarlar.telefon.replace(/[^\d+]/g, "")}`,
        },
        whatsapp && { ikon: WhatsappLogoIcon, etiket: "WhatsApp ile yazın", href: `https://wa.me/${whatsapp}` },
        ayarlar.adres && { ikon: MapPinIcon, etiket: ayarlar.adres, href: null },
      ].filter((x): x is { ikon: typeof EnvelopeSimpleIcon; etiket: string; href: string | null } => Boolean(x))
    : [];

  return (
    <Section arka_plan="gri" aria-labelledby={baslikId} className="overflow-hidden">
      <div aria-hidden className="absolute top-0 right-0 -z-10 size-[32rem] translate-x-1/3 -translate-y-1/3 rounded-full bg-primary/10 blur-3xl" />
      <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-5">
          <SectionHeading
            ust_baslik={veri.ust_baslik}
            baslik={veri.baslik}
            aciklama={veri.aciklama}
            baslikId={baslikId}
            hizalama="sol"
            altBosluk={false}
            className="mb-10"
          />
          {veri.maddeler?.length ? (
            <Stagger as="ul" className="space-y-5">
              {veri.maddeler.map((m, i) => (
                <StaggerItem as="li" key={i} className="flex gap-4">
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-zemin-kart text-primary shadow-kart ring-1 ring-zemin-cizgi">
                    <Icon ad={m.ikon} boyut={24} />
                  </span>
                  <span>
                    <span className="block font-display text-lg font-semibold text-zemin-baslik">{m.baslik}</span>
                    {m.metin ? <span className="mt-1 block leading-relaxed text-zemin-soluk">{m.metin}</span> : null}
                  </span>
                </StaggerItem>
              ))}
            </Stagger>
          ) : null}
          {iletisim.length ? (
            <Reveal gecikme={0.15} className="mt-10 rounded-kart border border-zemin-cizgi bg-zemin-kart p-6 shadow-kart">
              <h3 className="font-display text-base font-semibold text-zemin-baslik">İletişim bilgileri</h3>
              <ul className="mt-4 space-y-3">
                {iletisim.map(({ ikon: Ikon, etiket, href }) => (
                  <li key={etiket}>
                    {href ? (
                      <a
                        href={href}
                        {...(href.startsWith("https://") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                        className="group inline-flex items-center gap-3 text-zemin-metin transition-colors hover:text-zemin-vurgu"
                      >
                        <span className="flex size-9 items-center justify-center rounded-xl bg-primary-soft text-primary transition-transform group-hover:scale-110">
                          <Ikon aria-hidden size={18} weight="duotone" />
                        </span>
                        {etiket}
                      </a>
                    ) : (
                      <span className="inline-flex items-start gap-3 text-zemin-soluk">
                        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                          <Ikon aria-hidden size={18} weight="duotone" />
                        </span>
                        <span className="whitespace-pre-line pt-1.5">{etiket}</span>
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </Reveal>
          ) : null}
        </div>

        <Reveal gecikme={0.1} className="lg:col-span-7">
          <div className="relative rounded-panel bg-linear-to-br from-primary/40 via-zemin-cizgi to-zemin-cizgi p-px shadow-kart-hover">
            <div className="rounded-[calc(var(--radius-panel)-1px)] bg-zemin-kart p-6 sm:p-8 md:p-10">
              <BasvuruFormIstemci tip={veri.form_tipi} basariMesaji={veri.basari_mesaji} kvkkHref={kvkkHref} />
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}