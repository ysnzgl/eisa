/**
 * zengin_metin — Zengin Metin (KVKK, çerez politikası, serbest metin). CONTRACT §8.
 * `icerik_html` backend'de nh3 ile sanitize edilmiştir; `.prose-eisa` ile biçimlenir.
 * En az 3 başlık (h2/h3) varsa masaüstünde yapışkan "İçindekiler" menüsü gösterilir;
 * başlıklara sunucuda id eklenir.
 */

import { Icindekiler, type IcindekilerOgesi } from "@/components/blocks/Icindekiler";
import { Reveal } from "@/components/ui/Reveal";
import { Section } from "@/components/ui/Section";
import type { ZenginMetinVeri } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { BlokProps } from "./types";

const TR_HARF: Record<string, string> = { ç: "c", ğ: "g", ı: "i", ö: "o", ş: "s", ü: "u", â: "a", î: "i", û: "u" };

function slugla(metin: string): string {
  return metin
    .toLocaleLowerCase("tr-TR")
    .replace(/[çğıöşüâîû]/g, (h) => TR_HARF[h] ?? h)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

function metneCevir(html: string): string {
  return html
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;/g, "'")
    .trim();
}

/** h2/h3'lere benzersiz id ekler ve içindekiler listesini döner. */
function basliklariIsle(html: string, onEk: string): { html: string; ogeler: IcindekilerOgesi[] } {
  const ogeler: IcindekilerOgesi[] = [];
  const kullanilan = new Set<string>();
  const yeni = html.replace(/<h([23])(\s[^>]*)?>([\s\S]*?)<\/h\1>/gi, (tam, seviye: string, nitelik: string | undefined, ic: string) => {
    if (nitelik && /\sid\s*=/.test(nitelik)) return tam;
    const metin = metneCevir(ic);
    if (!metin) return tam;
    let id = `${onEk}-${slugla(metin) || "bolum"}`;
    for (let i = 2; kullanilan.has(id); i++) id = `${onEk}-${slugla(metin)}-${i}`;
    kullanilan.add(id);
    ogeler.push({ id, metin, seviye: seviye === "3" ? 3 : 2 });
    return `<h${seviye} id="${id}"${nitelik ?? ""}>${ic}</h${seviye}>`;
  });
  return { html: yeni, ogeler };
}

export default function ZenginMetin({ veri, blokId }: BlokProps<ZenginMetinVeri>) {
  const genis = veri.genislik === "genis";
  const baslikId = `${blokId}-baslik`;
  const { html, ogeler } = basliklariIsle(veri.icerik_html || "", blokId);
  const icindekiler = ogeler.length >= 3;

  const baslikVeTarih = (
    <>
      {veri.baslik ? (
        <h2 id={baslikId} className="mb-6 font-display text-3xl font-bold text-zemin-baslik md:text-4xl">
          {veri.baslik}
        </h2>
      ) : null}
      {veri.son_guncelleme ? (
        <p className="mb-10 inline-flex items-center gap-2 rounded-full border border-zemin-cizgi bg-zemin-kart px-4 py-1.5 text-sm text-zemin-soluk">
          <span aria-hidden className="size-1.5 rounded-full bg-primary" />
          Son güncelleme: {veri.son_guncelleme}
        </p>
      ) : null}
    </>
  );

  const icerik = (
    <div
      className={cn("prose-eisa", (genis || icindekiler) && "prose-eisa-genis")}
      // İçerik backend'de nh3 ile sanitize edilir (CONTRACT §5); yalnızca başlıklara id eklenir.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );

  if (icindekiler) {
    return (
      <Section arka_plan="acik" aria-labelledby={veri.baslik ? baslikId : undefined}>
        <div className="grid gap-12 lg:grid-cols-12">
          <aside className="hidden lg:col-span-3 lg:block">
            <div className="sticky top-[calc(var(--header-yukseklik-dar)+var(--onizleme-bant)+2rem)]">
              <Icindekiler ogeler={ogeler} />
            </div>
          </aside>
          <Reveal className="lg:col-span-9">
            {baslikVeTarih}
            {icerik}
          </Reveal>
        </div>
      </Section>
    );
  }

  return (
    <Section arka_plan="acik" genislik={genis ? "orta" : "dar"} aria-labelledby={veri.baslik ? baslikId : undefined}>
      <Reveal>
        {baslikVeTarih}
        {icerik}
      </Reveal>
    </Section>
  );
}