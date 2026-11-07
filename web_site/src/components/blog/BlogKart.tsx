/**
 * Blog yazı kartı — blog listesi, ilgili yazılar ve `blog_son_yazilar` bloğu ortak kullanır.
 */

import Link from "next/link";
import { ArrowRightIcon } from "@phosphor-icons/react/dist/ssr/ArrowRight";
import { MediaImage } from "@/components/ui/MediaImage";
import type { BlogOzet } from "@/lib/types";
import { cn, tarihFormatla } from "@/lib/utils";

export function BlogKart({
  yazi,
  baslikSeviyesi = "h3",
  className,
}: {
  yazi: BlogOzet;
  baslikSeviyesi?: "h2" | "h3";
  className?: string;
}) {
  const Baslik = baslikSeviyesi;
  return (
    <article
      className={cn(
        "group relative flex h-full flex-col overflow-hidden rounded-kart border border-zemin-cizgi bg-zemin-kart shadow-kart transition-all duration-300 hover:-translate-y-1 hover:shadow-kart-hover",
        className,
      )}
    >
      <div className="relative aspect-[16/9] overflow-hidden bg-dark">
        <MediaImage
          medya={yazi.kapak}
          fill
          sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
          className="object-cover transition-transform duration-500 group-hover:scale-105"
        >
          <div aria-hidden className="doku-izgara absolute inset-0 flex items-end bg-linear-to-br from-dark via-dark-2 to-brand-deep p-5">
            <span className="font-display text-lg font-semibold text-white/80">{yazi.kategori?.ad ?? "e-isa Blog"}</span>
            <span className="absolute top-5 right-5 size-10 rounded-full bg-primary/80 blur-xl" />
          </div>
        </MediaImage>
      </div>
      <div className="flex flex-1 flex-col p-6">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-medium text-zemin-soluk">
          {yazi.kategori ? <span className="text-zemin-vurgu">{yazi.kategori.ad}</span> : null}
          <time dateTime={yazi.yayin_tarihi}>{tarihFormatla(yazi.yayin_tarihi)}</time>
          {yazi.okuma_suresi ? <span>{yazi.okuma_suresi} dk okuma</span> : null}
        </div>
        <Baslik className="mt-3 text-xl leading-snug font-semibold text-zemin-baslik">
          <Link href={`/blog/${yazi.slug}`} className="after:absolute after:inset-0 after:content-['']">
            {yazi.baslik}
          </Link>
        </Baslik>
        {yazi.ozet ? <p className="mt-3 line-clamp-3 text-[0.9375rem] leading-relaxed text-zemin-soluk">{yazi.ozet}</p> : null}
        <span aria-hidden className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-semibold text-zemin-vurgu">
          Devamını oku
          <ArrowRightIcon weight="bold" className="size-4 transition-transform group-hover:translate-x-1" />
        </span>
      </div>
    </article>
  );
}
