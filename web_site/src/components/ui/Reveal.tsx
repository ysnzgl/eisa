"use client";

/**
 * Scroll reveal animasyonları (motion `whileInView`, bir kez).
 *
 *   <Reveal>...</Reveal>                         // aşağıdan yukarı belirme
 *   <Reveal yon="sol" gecikme={0.1}>...</Reveal>
 *   <Stagger className="grid ..."><StaggerItem>…</StaggerItem>…</Stagger>
 *
 * prefers-reduced-motion açıksa içerik animasyonsuz, anında görünür hale gelir.
 * (Hidrasyon uyumu için element tipi değişmez; yalnızca hedef değerlere süre 0 ile geçilir.)
 * Server component içinde kullanılabilir (children sunucuda render edilir).
 */

import { motion, type Variants } from "motion/react";
import type { ReactNode } from "react";
import { EASE_EISA } from "@/lib/hareket";
import { useAzHareket } from "@/lib/hooks";

type Etiket = "div" | "section" | "article" | "li" | "ul" | "ol" | "dl" | "span" | "p" | "header" | "figure";
export type RevealYon = "yukari" | "asagi" | "sol" | "sag" | "yok";

const HEDEF = { opacity: 1, x: 0, y: 0 };

function baslangic(yon: RevealYon, mesafe: number) {
  switch (yon) {
    case "yukari":
      return { opacity: 0, y: mesafe };
    case "asagi":
      return { opacity: 0, y: -mesafe };
    case "sol":
      return { opacity: 0, x: mesafe };
    case "sag":
      return { opacity: 0, x: -mesafe };
    default:
      return { opacity: 0 };
  }
}

/** Modül seviyesinde sabit harita: render sırasında bileşen üretilmez. */
const MOTION: Record<Etiket, typeof motion.div> = {
  div: motion.div,
  section: motion.section as typeof motion.div,
  article: motion.article as typeof motion.div,
  li: motion.li as unknown as typeof motion.div,
  ul: motion.ul as unknown as typeof motion.div,
  ol: motion.ol as unknown as typeof motion.div,
  dl: motion.dl as unknown as typeof motion.div,
  span: motion.span as unknown as typeof motion.div,
  p: motion.p as unknown as typeof motion.div,
  header: motion.header as typeof motion.div,
  figure: motion.figure as typeof motion.div,
};

export interface RevealProps {
  children: ReactNode;
  as?: Etiket;
  className?: string;
  /** İçeriğin geldiği yön. Varsayılan "yukari" (aşağıdan yukarı). */
  yon?: RevealYon;
  /** px, varsayılan 24 */
  mesafe?: number;
  /** sn */
  gecikme?: number;
  /** sn, varsayılan 0.7 */
  sure?: number;
  /** Görünürlük eşiği (0-1), varsayılan 0.2 */
  esik?: number;
  id?: string;
}

export function Reveal({
  children,
  as = "div",
  className,
  yon = "yukari",
  mesafe = 24,
  gecikme = 0,
  sure = 0.7,
  esik = 0.2,
  id,
}: RevealProps) {
  const azHareket = useAzHareket();
  const M = MOTION[as];
  return (
    <M
      id={id}
      className={className}
      initial={baslangic(yon, mesafe)}
      whileInView={HEDEF}
      animate={azHareket ? HEDEF : undefined}
      viewport={{ once: true, amount: esik }}
      transition={azHareket ? { duration: 0 } : { duration: sure, delay: gecikme, ease: EASE_EISA }}
    >
      {children}
    </M>
  );
}

/* ------------------------------------------------------------------ */

export interface StaggerProps {
  children: ReactNode;
  as?: Etiket;
  className?: string;
  /** Çocuklar arası gecikme (sn), varsayılan 0.08 */
  aralik?: number;
  gecikme?: number;
  esik?: number;
}

/** Çocuk `StaggerItem`'ları sırayla belirtir. */
export function Stagger({ children, as = "div", className, aralik = 0.08, gecikme = 0, esik = 0.15 }: StaggerProps) {
  const azHareket = useAzHareket();
  const M = MOTION[as];
  const varyant: Variants = {
    gizli: {},
    gorunur: {
      transition: azHareket ? { staggerChildren: 0 } : { staggerChildren: aralik, delayChildren: gecikme },
    },
  };
  return (
    <M
      className={className}
      variants={varyant}
      initial="gizli"
      whileInView="gorunur"
      animate={azHareket ? "gorunur" : undefined}
      viewport={{ once: true, amount: esik }}
    >
      {children}
    </M>
  );
}

export interface StaggerItemProps {
  children: ReactNode;
  as?: Etiket;
  className?: string;
  yon?: RevealYon;
  mesafe?: number;
  sure?: number;
}

export function StaggerItem({ children, as = "div", className, yon = "yukari", mesafe = 24, sure = 0.6 }: StaggerItemProps) {
  const azHareket = useAzHareket();
  const M = MOTION[as];
  const varyant: Variants = {
    gizli: baslangic(yon, mesafe),
    gorunur: { ...HEDEF, transition: azHareket ? { duration: 0 } : { duration: sure, ease: EASE_EISA } },
  };
  return (
    <M className={className} variants={varyant}>
      {children}
    </M>
  );
}
