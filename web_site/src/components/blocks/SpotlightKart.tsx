"use client";

/**
 * Fareyi takip eden yumuşak kırmızı ışık lekesi olan kart sarmalayıcısı.
 * İçerik sunucuda render edilir (children). Dokunmatikte yalnızca statik kart.
 */

import { useRef, type PointerEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function SpotlightKart({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const hareket = (e: PointerEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el || e.pointerType !== "mouse") return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--isik-x", `${e.clientX - r.left}px`);
    el.style.setProperty("--isik-y", `${e.clientY - r.top}px`);
  };
  return (
    <div ref={ref} onPointerMove={hareket} className={cn("group/kart relative isolate overflow-hidden", className)}>
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-0 transition-opacity duration-500 group-hover/kart:opacity-100"
        style={{
          background:
            "radial-gradient(380px circle at var(--isik-x, 50%) var(--isik-y, 0%), rgb(237 28 36 / 0.12), transparent 50%)",
        }}
      />
      {children}
    </div>
  );
}