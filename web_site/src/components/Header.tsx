"use client";

/**
 * Site header'ı.
 *
 * - Menü öğeleri API'den gelir (layout → prop). `cta=true` öğe kırmızı buton olarak sağda gösterilir.
 * - Alt menüler: hover ile açılır; klavyede ok (caret) butonu ile aç/kapa, Esc ile kapanır,
 *   ↓ ile ilk öğeye odaklanır (disclosure navigation deseni).
 * - Scroll'da daralır ve cam efekti alır. Sayfa koyu bir başlık bloğuyla başlıyorsa
 *   (BlockRenderer `data-ilk-blok="koyu"`) en üstteyken açık renk metin/beyaz logo (globals.css).
 * - Mobilde tam ekran animasyonlu menü: focus trap, Esc, gövde kaydırma kilidi.
 * - Aktif link: sayfa yolu eşleşmesi; anasayfa bölüm linkleri için scroll-spy.
 */

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useId, useRef, useState, useSyncExternalStore, type KeyboardEvent } from "react";
import { CaretDownIcon } from "@phosphor-icons/react/dist/ssr/CaretDown";
import { ListIcon } from "@phosphor-icons/react/dist/ssr/List";
import { XIcon } from "@phosphor-icons/react/dist/ssr/X";
import { ArrowRightIcon } from "@phosphor-icons/react/dist/ssr/ArrowRight";
import { EnvelopeSimpleIcon } from "@phosphor-icons/react/dist/ssr/EnvelopeSimple";
import { Logo } from "@/components/Logo";
import { SosyalLinkler } from "@/components/SosyalLinkler";
import { AkilliLink } from "@/components/ui/AkilliLink";
import { butonSiniflari } from "@/components/ui/ButonLink";
import { Container } from "@/components/ui/Container";
import { MagneticButton } from "@/components/ui/MagneticButton";
import { EASE_EISA } from "@/lib/hareket";
import { useAzHareket } from "@/lib/hooks";
import { headerOffset, kaydirmaKilidi } from "@/lib/kaydirma";
import type { MenuItem, SiteAyarlari } from "@/lib/types";
import { cn, disLinkMi, hrefAyir, yolNormalize } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Scroll durumları (useSyncExternalStore: SSR'da güvenli varsayılan)   */
/* ------------------------------------------------------------------ */

function scrollAbone(bildir: () => void) {
  window.addEventListener("scroll", bildir, { passive: true });
  window.addEventListener("resize", bildir);
  return () => {
    window.removeEventListener("scroll", bildir);
    window.removeEventListener("resize", bildir);
  };
}

function useKaydirildi(esik = 16): boolean {
  return useSyncExternalStore(
    scrollAbone,
    () => window.scrollY > esik,
    () => false,
  );
}

/** Verilen id'lerden, header'ın hemen altına gelmiş son bölüm (scroll-spy). */
function useAktifBolum(idler: string[]): string | null {
  const anahtar = idler.join("|");
  const anlik = useCallback(() => {
    if (!anahtar) return null;
    const sinir = headerOffset() + 48;
    let aktif: string | null = null;
    for (const id of anahtar.split("|")) {
      const el = document.getElementById(id);
      if (!el) continue;
      const r = el.getBoundingClientRect();
      if (r.top <= sinir && r.bottom > sinir) aktif = id;
    }
    return aktif;
  }, [anahtar]);
  return useSyncExternalStore(scrollAbone, anlik, () => null);
}

/* ------------------------------------------------------------------ */
/* Aktif link hesaplama                                                */
/* ------------------------------------------------------------------ */

function linkAktifMi(href: string, pathname: string, aktifHash: string | null): boolean {
  if (!href || disLinkMi(href) || /^(mailto|tel):/i.test(href)) return false;
  const { yol, hash } = hrefAyir(href);
  const hedefYol = yolNormalize(yol ?? pathname);
  const mevcut = yolNormalize(pathname);
  if (hash) return hedefYol === mevcut && aktifHash === hash;
  if (hedefYol === mevcut) return hedefYol !== "/" || aktifHash === null;
  // Alt yollar: /blog/yazi → /blog aktif
  return hedefYol !== "/" && mevcut.startsWith(`${hedefYol}/`);
}

function ogeAktifMi(oge: MenuItem, pathname: string, aktifHash: string | null): boolean {
  if (oge.cocuklar.length) return oge.cocuklar.some((c) => linkAktifMi(c.href, pathname, aktifHash));
  return linkAktifMi(oge.href, pathname, aktifHash);
}

/** Bu sayfadaki bölüm linklerinin hash'leri (scroll-spy için). */
function sayfadakiHashler(menu: MenuItem[], pathname: string): string[] {
  const sonuc = new Set<string>();
  const mevcut = yolNormalize(pathname);
  const tara = (ogeler: MenuItem[]) => {
    for (const o of ogeler) {
      const { yol, hash } = hrefAyir(o.href);
      if (hash && yolNormalize(yol ?? pathname) === mevcut) sonuc.add(hash);
      if (o.cocuklar.length) tara(o.cocuklar);
    }
  };
  tara(menu);
  return [...sonuc];
}

/* ------------------------------------------------------------------ */
/* Header                                                              */
/* ------------------------------------------------------------------ */

export interface HeaderProps {
  menu: MenuItem[];
  ayarlar: Pick<SiteAyarlari, "site_adi" | "eposta" | "sosyal_linkler">;
}

export function Header({ menu, ayarlar }: HeaderProps) {
  const pathname = usePathname();
  const kaydirildi = useKaydirildi();
  const azHareket = useAzHareket();

  const normalOgeler = menu.filter((m) => !m.cta);
  const ctaOgeler = menu.filter((m) => m.cta);
  const aktifHash = useAktifBolum(sayfadakiHashler(menu, pathname));

  // Mobil menü: açıldığı yol saklanır → route değişince otomatik kapanır (effect'te setState yok).
  const [mobilAcikYol, setMobilAcikYol] = useState<string | null>(null);
  const mobilAcik = mobilAcikYol === pathname;
  const kapat = () => setMobilAcikYol(null);

  const headerRef = useRef<HTMLElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);

  // Gövde kaydırma kilidi + ilk odak + odak geri dönüşü
  useEffect(() => {
    if (!mobilAcik) return;
    kaydirmaKilidi(true);
    const toggle = toggleRef.current;
    const t = window.setTimeout(() => {
      headerRef.current?.querySelector<HTMLElement>("#mobil-menu a, #mobil-menu button")?.focus();
    }, 50);
    return () => {
      window.clearTimeout(t);
      kaydirmaKilidi(false);
      toggle?.focus({ preventScroll: true });
    };
  }, [mobilAcik]);

  // lg ve üstüne geçilirse mobil menüyü kapat
  useEffect(() => {
    if (!mobilAcik) return;
    const mql = window.matchMedia("(min-width: 1024px)");
    const dinle = () => {
      if (mql.matches) setMobilAcikYol(null);
    };
    mql.addEventListener("change", dinle);
    return () => mql.removeEventListener("change", dinle);
  }, [mobilAcik]);

  // Focus trap + Esc (header kapsamı: bar + overlay)
  const klavye = (e: KeyboardEvent<HTMLElement>) => {
    if (!mobilAcik) return;
    if (e.key === "Escape") {
      e.preventDefault();
      kapat();
      return;
    }
    if (e.key !== "Tab" || !headerRef.current) return;
    const odaklanabilir = Array.from(
      headerRef.current.querySelectorAll<HTMLElement>(
        '#mobil-menu a[href], #mobil-menu button:not([disabled]), [data-mobil-toggle], [data-header-logo]',
      ),
    ).filter((el) => el.offsetParent !== null || el === document.activeElement);
    if (!odaklanabilir.length) return;
    const ilk = odaklanabilir[0];
    const son = odaklanabilir[odaklanabilir.length - 1];
    if (e.shiftKey && document.activeElement === ilk) {
      e.preventDefault();
      son.focus();
    } else if (!e.shiftKey && document.activeElement === son) {
      e.preventDefault();
      ilk.focus();
    }
  };

  return (
    <header
      ref={headerRef}
      onKeyDown={klavye}
      data-kaydirildi={kaydirildi ? "true" : "false"}
      data-menu-acik={mobilAcik ? "true" : "false"}
      className="site-header group/header fixed inset-x-0 z-50 text-(--hdr-metin)"
      style={{ top: "var(--onizleme-bant)" }}
    >
      {/* Cam zemin katmanı */}
      <div
        aria-hidden
        className={cn(
          "cam absolute inset-0 border-b border-line/80 shadow-[0_8px_30px_-20px_rgb(11_15_20/0.35)] transition-opacity duration-500",
          kaydirildi && !mobilAcik ? "opacity-100" : "opacity-0",
        )}
      />

      <Container
        className={cn(
          "relative z-10 flex items-center justify-between gap-6 transition-[height] duration-500 ease-eisa",
          kaydirildi ? "h-(--header-yukseklik-dar)" : "h-(--header-yukseklik)",
        )}
      >
        <Link
          href="/"
          data-header-logo
          aria-label={`${ayarlar.site_adi || "e-isa"} — Anasayfa`}
          className="relative flex shrink-0 items-center rounded-lg"
          onClick={kapat}
        >
          <span className="logo-koyu">
            <Logo varyant="koyu" yukseklik={kaydirildi ? 30 : 36} priority />
          </span>
          <span className="logo-beyaz">
            <Logo varyant="beyaz" yukseklik={kaydirildi ? 30 : 36} priority />
          </span>
        </Link>

        {/* Masaüstü menü */}
        <nav aria-label="Ana menü" className="hidden lg:block">
          <ul className="flex items-center gap-1">
            {normalOgeler.map((oge) =>
              oge.cocuklar.length ? (
                <AltMenuluOge
                  key={oge.id}
                  oge={oge}
                  aktif={ogeAktifMi(oge, pathname, aktifHash)}
                  pathname={pathname}
                  aktifHash={aktifHash}
                  azHareket={azHareket}
                />
              ) : (
                <li key={oge.id}>
                  <MasaustuLink oge={oge} aktif={linkAktifMi(oge.href, pathname, aktifHash)} />
                </li>
              ),
            )}
          </ul>
        </nav>

        <div className="flex items-center gap-2">
          {ctaOgeler.map((oge) => (
            <MagneticButton key={oge.id} className="hidden lg:inline-flex">
              <AkilliLink href={oge.href} yeniSekme={oge.yeni_sekme} className={butonSiniflari("birincil", "kucuk")}>
                {oge.etiket}
                <ArrowRightIcon aria-hidden weight="bold" className="size-4" />
              </AkilliLink>
            </MagneticButton>
          ))}

          <button
            ref={toggleRef}
            type="button"
            data-mobil-toggle
            aria-label={mobilAcik ? "Menüyü kapat" : "Menüyü aç"}
            aria-expanded={mobilAcik}
            aria-controls="mobil-menu"
            onClick={() => setMobilAcikYol(mobilAcik ? null : pathname)}
            className="inline-flex size-11 items-center justify-center rounded-full transition-colors hover:bg-(--hdr-hover-zemin) lg:hidden"
          >
            {mobilAcik ? <XIcon aria-hidden size={24} /> : <ListIcon aria-hidden size={24} />}
          </button>
        </div>
      </Container>

      <AnimatePresence>
        {mobilAcik ? (
          <MobilMenu
            menu={menu}
            pathname={pathname}
            aktifHash={aktifHash}
            ayarlar={ayarlar}
            azHareket={azHareket}
            kapat={kapat}
          />
        ) : null}
      </AnimatePresence>
    </header>
  );
}

/* ------------------------------------------------------------------ */
/* Masaüstü parçaları                                                  */
/* ------------------------------------------------------------------ */

function MasaustuLink({ oge, aktif }: { oge: MenuItem; aktif: boolean }) {
  return (
    <AkilliLink
      href={oge.href}
      yeniSekme={oge.yeni_sekme}
      aria-current={aktif ? "page" : undefined}
      className={cn(
        "relative inline-flex h-10 items-center rounded-full px-3.5 text-[0.9375rem] font-medium transition-colors hover:bg-(--hdr-hover-zemin)",
        aktif ? "text-(--hdr-metin)" : "text-(--hdr-metin-soluk) hover:text-(--hdr-metin)",
      )}
    >
      {oge.etiket}
      {aktif ? (
        <span aria-hidden className="absolute bottom-1 left-1/2 size-1 -translate-x-1/2 rounded-full bg-primary" />
      ) : null}
    </AkilliLink>
  );
}

function AltMenuluOge({
  oge,
  aktif,
  pathname,
  aktifHash,
  azHareket,
}: {
  oge: MenuItem;
  aktif: boolean;
  pathname: string;
  aktifHash: string | null;
  azHareket: boolean;
}) {
  // Açık durum, açıldığı yol ile saklanır → route değişince kapanır.
  const [acikYol, setAcikYol] = useState<string | null>(null);
  const acik = acikYol === pathname;
  const kapatZamanlayici = useRef<number | null>(null);
  const butonRef = useRef<HTMLButtonElement>(null);
  const listeRef = useRef<HTMLUListElement>(null);
  const listeId = useId();

  const temizle = () => {
    if (kapatZamanlayici.current) window.clearTimeout(kapatZamanlayici.current);
    kapatZamanlayici.current = null;
  };
  const ac = () => {
    temizle();
    setAcikYol(pathname);
  };
  const kapat = () => {
    temizle();
    setAcikYol(null);
  };
  const gecikmeliKapat = () => {
    temizle();
    kapatZamanlayici.current = window.setTimeout(() => setAcikYol(null), 160);
  };

  const ilkOgeyeOdaklan = () => {
    window.requestAnimationFrame(() => listeRef.current?.querySelector<HTMLElement>("a")?.focus());
  };

  const butonKlavye = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      ac();
      ilkOgeyeOdaklan();
    } else if (e.key === "Escape" && acik) {
      e.preventDefault();
      kapat();
    }
  };

  const listeKlavye = (e: KeyboardEvent<HTMLUListElement>) => {
    const linkler = Array.from(listeRef.current?.querySelectorAll<HTMLElement>("a") ?? []);
    const i = linkler.indexOf(document.activeElement as HTMLElement);
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      kapat();
      butonRef.current?.focus();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      linkler[(i + 1) % linkler.length]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      linkler[(i - 1 + linkler.length) % linkler.length]?.focus();
    }
  };

  return (
    <li
      className="relative"
      onMouseEnter={ac}
      onMouseLeave={gecikmeliKapat}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) kapat();
      }}
    >
      <div className="flex items-center">
        <AkilliLink
          href={oge.href}
          yeniSekme={oge.yeni_sekme}
          className={cn(
            "relative inline-flex h-10 items-center rounded-l-full py-0 pr-1 pl-3.5 text-[0.9375rem] font-medium transition-colors",
            aktif || acik ? "text-(--hdr-metin)" : "text-(--hdr-metin-soluk) hover:text-(--hdr-metin)",
          )}
        >
          {oge.etiket}
          {aktif ? (
            <span aria-hidden className="absolute bottom-1 left-[calc(50%+0.25rem)] size-1 -translate-x-1/2 rounded-full bg-primary" />
          ) : null}
        </AkilliLink>
        <button
          ref={butonRef}
          type="button"
          aria-expanded={acik}
          aria-controls={listeId}
          aria-label={`${oge.etiket} alt menüsü`}
          onClick={() => (acik ? kapat() : ac())}
          onKeyDown={butonKlavye}
          className={cn(
            "inline-flex h-10 w-7 items-center justify-center rounded-r-full transition-colors",
            acik ? "text-(--hdr-metin)" : "text-(--hdr-metin-soluk) hover:text-(--hdr-metin)",
          )}
        >
          <CaretDownIcon
            aria-hidden
            weight="bold"
            className={cn("size-3.5 transition-transform duration-300", acik && "rotate-180")}
          />
        </button>
      </div>

      <AnimatePresence>
        {acik ? (
          <motion.ul
            ref={listeRef}
            id={listeId}
            onKeyDown={listeKlavye}
            initial={azHareket ? false : { opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={azHareket ? { opacity: 0, transition: { duration: 0 } } : { opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.22, ease: EASE_EISA }}
            className="absolute top-full left-0 mt-2 min-w-60 origin-top-left rounded-2xl border border-line bg-card p-2 text-ink shadow-kart-hover"
          >
            {oge.cocuklar.map((c) => {
              const cAktif = linkAktifMi(c.href, pathname, aktifHash);
              return (
                <li key={c.id}>
                  <AkilliLink
                    href={c.href}
                    yeniSekme={c.yeni_sekme}
                    aria-current={cAktif ? "page" : undefined}
                    onClick={kapat}
                    className={cn(
                      "group/alt flex items-center justify-between gap-4 rounded-xl px-3.5 py-2.5 text-[0.9375rem] font-medium transition-colors hover:bg-gri",
                      cAktif ? "text-primary-hover" : "text-ink",
                    )}
                  >
                    {c.etiket}
                    <ArrowRightIcon
                      aria-hidden
                      weight="bold"
                      className="size-3.5 -translate-x-1 opacity-0 transition-all duration-300 group-hover/alt:translate-x-0 group-hover/alt:opacity-100"
                    />
                  </AkilliLink>
                </li>
              );
            })}
          </motion.ul>
        ) : null}
      </AnimatePresence>
    </li>
  );
}

/* ------------------------------------------------------------------ */
/* Mobil menü                                                          */
/* ------------------------------------------------------------------ */

function MobilMenu({
  menu,
  pathname,
  aktifHash,
  ayarlar,
  azHareket,
  kapat,
}: {
  menu: MenuItem[];
  pathname: string;
  aktifHash: string | null;
  ayarlar: HeaderProps["ayarlar"];
  azHareket: boolean;
  kapat: () => void;
}) {
  const normal = menu.filter((m) => !m.cta);
  const cta = menu.filter((m) => m.cta);

  const kapsayici = {
    gizli: {},
    gorunur: { transition: { staggerChildren: azHareket ? 0 : 0.05, delayChildren: azHareket ? 0 : 0.15 } },
  };
  const oge = {
    gizli: azHareket ? { opacity: 0 } : { opacity: 0, y: 24 },
    gorunur: { opacity: 1, y: 0, transition: { duration: azHareket ? 0 : 0.5, ease: EASE_EISA } },
  };

  return (
    <motion.div
      id="mobil-menu"
      role="dialog"
      aria-modal="true"
      aria-label="Site menüsü"
      data-zemin="koyu"
      className="fixed inset-0 z-0 overflow-hidden bg-dark text-white lg:hidden"
      initial={azHareket ? { opacity: 0 } : { clipPath: "circle(0% at calc(100% - 2.75rem) 2.5rem)" }}
      animate={azHareket ? { opacity: 1 } : { clipPath: "circle(150% at calc(100% - 2.75rem) 2.5rem)" }}
      exit={azHareket ? { opacity: 0 } : { clipPath: "circle(0% at calc(100% - 2.75rem) 2.5rem)" }}
      transition={{ duration: azHareket ? 0 : 0.6, ease: EASE_EISA }}
    >
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-32 -right-24 h-96 w-96 rounded-full bg-primary/30 blur-[110px]" />
        <div className="absolute -bottom-40 -left-24 h-96 w-96 rounded-full bg-[#2b6cb0]/20 blur-[110px]" />
      </div>

      <nav
        aria-label="Mobil menü"
        data-lenis-prevent
        className="relative flex h-full flex-col overflow-y-auto px-6 pt-[calc(var(--header-yukseklik)+var(--onizleme-bant)+1rem)] pb-10"
      >
        <motion.ul variants={kapsayici} initial="gizli" animate="gorunur" className="flex flex-col gap-1">
          {normal.map((m) => {
            const aktif = ogeAktifMi(m, pathname, aktifHash);
            return (
              <motion.li key={m.id} variants={oge} className="border-b border-white/10 py-3">
                <AkilliLink
                  href={m.href}
                  yeniSekme={m.yeni_sekme}
                  onClick={kapat}
                  aria-current={aktif && !m.cocuklar.length ? "page" : undefined}
                  className={cn(
                    "flex items-center justify-between font-display text-3xl font-semibold tracking-tight",
                    aktif ? "text-white" : "text-white/85",
                  )}
                >
                  <span className="flex items-center gap-3">
                    {aktif ? <span aria-hidden className="size-2 rounded-full bg-primary" /> : null}
                    {m.etiket}
                  </span>
                </AkilliLink>
                {m.cocuklar.length ? (
                  <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 pl-1">
                    {m.cocuklar.map((c) => {
                      const cAktif = linkAktifMi(c.href, pathname, aktifHash);
                      return (
                        <li key={c.id}>
                          <AkilliLink
                            href={c.href}
                            yeniSekme={c.yeni_sekme}
                            onClick={kapat}
                            aria-current={cAktif ? "page" : undefined}
                            className={cn(
                              "inline-flex py-1 text-base transition-colors",
                              cAktif ? "text-[#ff5a60]" : "text-white/65 hover:text-white",
                            )}
                          >
                            {c.etiket}
                          </AkilliLink>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </motion.li>
            );
          })}
        </motion.ul>

        <motion.div variants={oge} initial="gizli" animate="gorunur" className="mt-auto pt-10">
          {cta.map((m) => (
            <AkilliLink
              key={m.id}
              href={m.href}
              yeniSekme={m.yeni_sekme}
              onClick={kapat}
              className={butonSiniflari("birincil", "buyuk", "w-full")}
            >
              {m.etiket}
              <ArrowRightIcon aria-hidden weight="bold" className="size-4" />
            </AkilliLink>
          ))}
          <div className="mt-8 flex items-center justify-between gap-4 text-white/70">
            {ayarlar.eposta ? (
              <a
                href={`mailto:${ayarlar.eposta}`}
                className="inline-flex items-center gap-2 text-sm transition-colors hover:text-white"
              >
                <EnvelopeSimpleIcon aria-hidden size={18} />
                {ayarlar.eposta}
              </a>
            ) : (
              <span />
            )}
            <SosyalLinkler linkler={ayarlar.sosyal_linkler} varyant="koyu" />
          </div>
        </motion.div>
      </nav>
    </motion.div>
  );
}
