import { cn, paragraflaraBol } from "@/lib/utils";

export interface ParagraflarProps {
  /** CONTRACT `uzun_metin`: çift satır sonu paragraf ayırır, tek satır sonu korunur. */
  metin: string | null | undefined;
  className?: string;
  paragrafClassName?: string;
}

/** `uzun_metin` → <p>'ler. Boşsa null. */
export function Paragraflar({ metin, className, paragrafClassName }: ParagraflarProps) {
  const paragraflar = paragraflaraBol(metin);
  if (!paragraflar.length) return null;
  return (
    <div className={cn("space-y-4", className)}>
      {paragraflar.map((p, i) => (
        <p key={i} className={cn("whitespace-pre-line", paragrafClassName)}>
          {p}
        </p>
      ))}
    </div>
  );
}
