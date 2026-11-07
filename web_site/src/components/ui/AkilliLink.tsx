"use client";

/**
 * Akıllı link: href türüne göre doğru davranışı seçer.
 *
 * - `/yol`               → next/link (istemci tarafı geçiş)
 * - `#anchor`            → aynı sayfada header offset'li yumuşak kaydırma
 * - `/yol#anchor`        → aynı sayfadaysa kaydırma; değilse next/link ile git, SmoothScroll konumlandırır
 * - `https://...`        → yeni sekme, rel="noopener noreferrer"
 * - `mailto:` / `tel:`   → düz <a>
 *
 * Header, Footer, ButonLink ve bloklar iç/dış tüm linkler için bunu kullanmalıdır.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { AnchorHTMLAttributes, MouseEvent, ReactNode } from "react";
import { hedefeKaydir } from "@/lib/kaydirma";
import { disLinkMi, hrefAyir, icLinkMi, semaLinkiMi, yolNormalize } from "@/lib/utils";

export interface AkilliLinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  href: string;
  /** Menü öğesindeki `yeni_sekme`. Dış linkler her zaman yeni sekmede açılır. */
  yeniSekme?: boolean;
  children: ReactNode;
  /** next/link prefetch (varsayılan: Next varsayılanı) */
  prefetch?: boolean;
}

export function AkilliLink({ href, yeniSekme, children, onClick, prefetch, ...rest }: AkilliLinkProps) {
  const pathname = usePathname();

  // mailto:, tel:
  if (semaLinkiMi(href)) {
    return (
      <a href={href} onClick={onClick} {...rest}>
        {children}
      </a>
    );
  }

  // Dış link
  if (disLinkMi(href)) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" onClick={onClick} {...rest}>
        {children}
        <span className="sr-only"> (yeni sekmede açılır)</span>
      </a>
    );
  }

  const { yol, hash } = hrefAyir(href);
  const ayniSayfa = hash !== null && (yol === null || yolNormalize(yol) === yolNormalize(pathname));

  const tiklandi = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented) return;
    // Yeni sekme / orta tık / değiştirici tuşlar: tarayıcıya bırak
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || yeniSekme) return;
    if (ayniSayfa && hash) {
      if (hedefeKaydir(hash)) {
        e.preventDefault();
        const yeniUrl = `${window.location.pathname}${window.location.search}#${encodeURIComponent(hash)}`;
        if (window.location.hash !== `#${hash}`) window.history.pushState(null, "", yeniUrl);
      }
    }
  };

  const hedefOzellikleri = yeniSekme ? { target: "_blank", rel: "noopener noreferrer" } : {};

  // Saf anchor (#x): next/link gerekmez
  if (yol === null) {
    return (
      <a href={href} onClick={tiklandi} {...hedefOzellikleri} {...rest}>
        {children}
      </a>
    );
  }

  if (icLinkMi(href)) {
    return (
      <Link href={href} onClick={tiklandi} prefetch={prefetch} {...hedefOzellikleri} {...rest}>
        {children}
      </Link>
    );
  }

  // Tanınmayan biçim: güvenli düz link
  return (
    <a href={href} onClick={onClick} {...rest}>
      {children}
    </a>
  );
}
