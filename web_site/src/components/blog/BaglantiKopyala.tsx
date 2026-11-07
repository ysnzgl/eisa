"use client";

import { useState } from "react";
import { CheckIcon } from "@phosphor-icons/react/dist/ssr/Check";
import { LinkSimpleIcon } from "@phosphor-icons/react/dist/ssr/LinkSimple";

/** Bağlantıyı panoya kopyalar (paylaşım satırı için). */
export function BaglantiKopyala({ url }: { url: string }) {
  const [kopyalandi, setKopyalandi] = useState(false);
  const kopyala = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setKopyalandi(true);
      window.setTimeout(() => setKopyalandi(false), 2000);
    } catch {
      window.prompt("Bağlantıyı kopyalayın:", url);
    }
  };
  return (
    <button
      type="button"
      onClick={kopyala}
      aria-label={kopyalandi ? "Bağlantı kopyalandı" : "Bağlantıyı kopyala"}
      className="inline-flex size-10 items-center justify-center rounded-full border border-line text-muted transition-colors hover:border-primary hover:text-primary-hover"
    >
      {kopyalandi ? <CheckIcon aria-hidden size={18} weight="bold" /> : <LinkSimpleIcon aria-hidden size={18} />}
      <span aria-live="polite" className="sr-only">
        {kopyalandi ? "Bağlantı kopyalandı" : ""}
      </span>
    </button>
  );
}
