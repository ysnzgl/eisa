"use client";

/**
 * Mıknatıs etkisi: imleç yaklaştıkça içerik hafifçe imlece doğru kayar.
 * Yalnızca hassas işaretçide (fare) ve reduced-motion kapalıyken çalışır; aksi halde düz sarmalayıcı.
 */

import { motion, useMotionValue, useSpring } from "motion/react";
import { useRef, type PointerEvent, type ReactNode } from "react";
import { useAzHareket, useInceIsaretci } from "@/lib/hooks";
import { cn } from "@/lib/utils";

export interface MagneticButtonProps {
  children: ReactNode;
  /** 0-1 arası çekim gücü, varsayılan 0.3 */
  guc?: number;
  className?: string;
}

export function MagneticButton({ children, guc = 0.3, className }: MagneticButtonProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const azHareket = useAzHareket();
  const inceIsaretci = useInceIsaretci();
  const aktif = inceIsaretci && !azHareket;

  const x = useSpring(useMotionValue(0), { stiffness: 220, damping: 18, mass: 0.4 });
  const y = useSpring(useMotionValue(0), { stiffness: 220, damping: 18, mass: 0.4 });

  const hareket = (e: PointerEvent<HTMLSpanElement>) => {
    if (!aktif || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    x.set((e.clientX - (r.left + r.width / 2)) * guc);
    y.set((e.clientY - (r.top + r.height / 2)) * guc);
  };
  const birak = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.span
      ref={ref}
      className={cn("inline-flex", className)}
      style={aktif ? { x, y } : undefined}
      onPointerMove={hareket}
      onPointerLeave={birak}
    >
      {children}
    </motion.span>
  );
}
