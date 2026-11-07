"use client";

/** Görünür olunca soldan sağa (veya yukarıdan aşağı) çizilen ince kırmızı çizgi. */

import { motion } from "motion/react";
import { EASE_EISA } from "@/lib/hareket";
import { useAzHareket } from "@/lib/hooks";
import { cn } from "@/lib/utils";

export function CizilenCizgi({ yon = "yatay", className }: { yon?: "yatay" | "dikey"; className?: string }) {
  const azHareket = useAzHareket();
  const yatay = yon === "yatay";
  return (
    <span aria-hidden className={cn("block", yatay ? "h-px" : "w-px", className)}>
      <span className={cn("absolute inset-0 bg-zemin-cizgi")} />
      <motion.span
        className={cn(
          "absolute inset-0 bg-linear-to-r from-primary via-primary to-primary/30",
          yatay ? "origin-left" : "origin-top bg-linear-to-b",
        )}
        initial={yatay ? { scaleX: 0 } : { scaleY: 0 }}
        whileInView={yatay ? { scaleX: 1 } : { scaleY: 1 }}
        viewport={{ once: true, amount: 0.6 }}
        transition={azHareket ? { duration: 0 } : { duration: 1.4, ease: EASE_EISA, delay: 0.2 }}
      />
    </span>
  );
}