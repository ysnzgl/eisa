/**
 * Site footer'ı (server component). İçerik tamamen site ayarları + footer menülerinden gelir.
 * Boş iletişim alanları gizlenir.
 */

import { EnvelopeSimpleIcon } from "@phosphor-icons/react/dist/ssr/EnvelopeSimple";
import { MapPinIcon } from "@phosphor-icons/react/dist/ssr/MapPin";
import { PhoneIcon } from "@phosphor-icons/react/dist/ssr/Phone";
import { WhatsappLogoIcon } from "@phosphor-icons/react/dist/ssr/WhatsappLogo";
import { Logo } from "@/components/Logo";
import { SosyalLinkler } from "@/components/SosyalLinkler";
import { AkilliLink } from "@/components/ui/AkilliLink";
import { Container } from "@/components/ui/Container";
import type { SiteData } from "@/lib/types";
import { cn } from "@/lib/utils";

function telHref(telefon: string): string {
  return `tel:${telefon.replace(/[^\d+]/g, "")}`;
}

function whatsappHref(numara: string): string {
  if (/^https?:\/\//i.test(numara)) return numara;
  return `https://wa.me/${numara.replace(/\D/g, "")}`;
}

export function Footer({ site }: { site: SiteData }) {
  const { ayarlar, menuler } = site;
  const yil = new Date().getFullYear();
  const iletisimVar = Boolean(ayarlar.eposta || ayarlar.telefon || ayarlar.whatsapp || ayarlar.adres);
  const linkSinifi = "text-sm text-white/65 transition-colors hover:text-white";

  return (
    <footer data-zemin="koyu" className="relative isolate overflow-hidden bg-dark text-white">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 right-[-10%] h-[28rem] w-[28rem] rounded-full bg-primary/15 blur-[120px]" />
        <div className="absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-white/20 to-transparent" />
      </div>

      <Container className="pt-20 pb-10">
        <div className="grid gap-12 lg:grid-cols-12">
          {/* Marka */}
          <div className="lg:col-span-4">
            <Logo varyant="beyaz" yukseklik={44} alt={ayarlar.site_adi || "e-isa"} />
            {ayarlar.footer_aciklama ? (
              <p className="mt-6 max-w-sm text-sm leading-relaxed text-white/60">{ayarlar.footer_aciklama}</p>
            ) : null}
            <SosyalLinkler linkler={ayarlar.sosyal_linkler} varyant="koyu" className="mt-6" />
          </div>

          {/* Menü sütunları */}
          <div
            className={cn(
              "grid gap-10 sm:grid-cols-2 lg:col-span-8",
              iletisimVar ? "lg:grid-cols-3" : "lg:grid-cols-2",
            )}
          >
            {menuler.footer.map((sutun) => (
              <nav key={sutun.id} aria-label={sutun.etiket}>
                <h2 className="eyebrow text-white/90">{sutun.etiket}</h2>
                <ul className="mt-5 space-y-3">
                  {sutun.cocuklar.map((l) => (
                    <li key={l.id}>
                      <AkilliLink href={l.href} yeniSekme={l.yeni_sekme} className={linkSinifi}>
                        {l.etiket}
                      </AkilliLink>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}

            {iletisimVar ? (
              <div>
                <h2 className="eyebrow text-white/90">İletişim</h2>
                <ul className="mt-5 space-y-3">
                  {ayarlar.eposta ? (
                    <li>
                      <a href={`mailto:${ayarlar.eposta}`} className={cn(linkSinifi, "inline-flex items-center gap-2")}>
                        <EnvelopeSimpleIcon aria-hidden size={18} className="shrink-0 text-primary" />
                        {ayarlar.eposta}
                      </a>
                    </li>
                  ) : null}
                  {ayarlar.telefon ? (
                    <li>
                      <a href={telHref(ayarlar.telefon)} className={cn(linkSinifi, "inline-flex items-center gap-2")}>
                        <PhoneIcon aria-hidden size={18} className="shrink-0 text-primary" />
                        {ayarlar.telefon}
                      </a>
                    </li>
                  ) : null}
                  {ayarlar.whatsapp ? (
                    <li>
                      <a
                        href={whatsappHref(ayarlar.whatsapp)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={cn(linkSinifi, "inline-flex items-center gap-2")}
                      >
                        <WhatsappLogoIcon aria-hidden size={18} className="shrink-0 text-primary" />
                        WhatsApp<span className="sr-only"> (yeni sekmede açılır)</span>
                      </a>
                    </li>
                  ) : null}
                  {ayarlar.adres ? (
                    <li className="flex items-start gap-2 text-sm text-white/65">
                      <MapPinIcon aria-hidden size={18} className="mt-0.5 shrink-0 text-primary" />
                      <address className="not-italic whitespace-pre-line">{ayarlar.adres}</address>
                    </li>
                  ) : null}
                </ul>
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-16 flex flex-col-reverse gap-4 border-t border-white/10 pt-8 text-sm text-white/50 md:flex-row md:items-center md:justify-between">
          <p>
            © {yil} {ayarlar.firma_unvani.replace(/\.$/, "")}. Tüm hakları saklıdır.
          </p>
          {menuler.footer_alt.length ? (
            <nav aria-label="Yasal">
              <ul className="flex flex-wrap gap-x-6 gap-y-2">
                {menuler.footer_alt.map((l) => (
                  <li key={l.id}>
                    <AkilliLink href={l.href} yeniSekme={l.yeni_sekme} className="transition-colors hover:text-white">
                      {l.etiket}
                    </AkilliLink>
                  </li>
                ))}
              </ul>
            </nav>
          ) : null}
        </div>
      </Container>
    </footer>
  );
}
