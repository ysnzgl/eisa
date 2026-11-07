import type { Icon as PhosphorIkon } from "@phosphor-icons/react";
import { FacebookLogoIcon } from "@phosphor-icons/react/dist/ssr/FacebookLogo";
import { InstagramLogoIcon } from "@phosphor-icons/react/dist/ssr/InstagramLogo";
import { LinkedinLogoIcon } from "@phosphor-icons/react/dist/ssr/LinkedinLogo";
import { XLogoIcon } from "@phosphor-icons/react/dist/ssr/XLogo";
import { YoutubeLogoIcon } from "@phosphor-icons/react/dist/ssr/YoutubeLogo";
import type { SosyalLink, SosyalPlatform } from "@/lib/types";
import { cn } from "@/lib/utils";

const PLATFORM: Record<SosyalPlatform, { ad: string; ikon: PhosphorIkon }> = {
  linkedin: { ad: "LinkedIn", ikon: LinkedinLogoIcon },
  instagram: { ad: "Instagram", ikon: InstagramLogoIcon },
  x: { ad: "X (Twitter)", ikon: XLogoIcon },
  youtube: { ad: "YouTube", ikon: YoutubeLogoIcon },
  facebook: { ad: "Facebook", ikon: FacebookLogoIcon },
};

export interface SosyalLinklerProps {
  linkler: SosyalLink[] | null | undefined;
  varyant?: "acik" | "koyu";
  boyut?: number;
  className?: string;
}

/** Sosyal medya ikon linkleri (bilinmeyen platformlar atlanır). Boşsa null. */
export function SosyalLinkler({ linkler, varyant = "koyu", boyut = 20, className }: SosyalLinklerProps) {
  const gecerli = (linkler ?? []).filter((l) => l.url && PLATFORM[l.platform]);
  if (!gecerli.length) return null;
  return (
    <ul className={cn("flex items-center gap-2", className)}>
      {gecerli.map((l) => {
        const { ad, ikon: Ikon } = PLATFORM[l.platform];
        return (
          <li key={`${l.platform}-${l.url}`}>
            <a
              href={l.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${ad} (yeni sekmede açılır)`}
              className={cn(
                "inline-flex size-10 items-center justify-center rounded-full border transition-all duration-300 hover:-translate-y-0.5",
                varyant === "koyu"
                  ? "border-white/15 text-white/75 hover:border-primary hover:bg-primary hover:text-white"
                  : "border-line text-muted hover:border-primary hover:text-primary-hover",
              )}
            >
              <Ikon aria-hidden size={boyut} weight="regular" />
            </a>
          </li>
        );
      })}
    </ul>
  );
}
