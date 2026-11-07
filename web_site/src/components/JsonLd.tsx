/**
 * JSON-LD yapılandırılmış veri. Server component.
 *
 *   <JsonLd veri={{ "@context": "https://schema.org", "@type": "FAQPage", mainEntity: [...] }} />
 *
 * `<` karakteri kaçışlanır (script enjeksiyonuna karşı). Birden fazla şema için dizi verin.
 */

export type JsonLdVeri = Record<string, unknown> | Array<Record<string, unknown>>;

export function JsonLd({ veri }: { veri: JsonLdVeri }) {
  const json = JSON.stringify(veri).replace(/</g, "\\u003c");
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}
