import type { ElementType, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ContainerGenislik = "dar" | "orta" | "normal" | "genis";

const GENISLIK: Record<ContainerGenislik, string> = {
  dar: "max-w-3xl", // ~768px — zengin metin, form
  orta: "max-w-5xl", // ~1024px
  normal: "max-w-7xl", // ~1280px — varsayılan
  genis: "max-w-[90rem]", // ~1440px
};

export interface ContainerProps {
  children: ReactNode;
  genislik?: ContainerGenislik;
  as?: ElementType;
  className?: string;
}

/** Yatay hizalama + responsive iç boşluk. */
export function Container({ children, genislik = "normal", as: Etiket = "div", className }: ContainerProps) {
  return <Etiket className={cn("container-eisa", GENISLIK[genislik], className)}>{children}</Etiket>;
}
