/**
 * Ortak hareket sabitleri (motion). Sunucu ve istemci tarafında import edilebilir.
 */

/** Varsayılan yumuşak çıkış eğrisi (CSS: var(--ease-eisa)). */
export const EASE_EISA = [0.22, 1, 0.36, 1] as const;

export const SURE = {
  kisa: 0.3,
  orta: 0.6,
  uzun: 0.9,
} as const;

/** Yay (spring) ayarları — mıknatıs, hover vb. */
export const YAY = {
  yumusak: { type: "spring", stiffness: 160, damping: 18, mass: 0.4 },
  sert: { type: "spring", stiffness: 380, damping: 30 },
} as const;
