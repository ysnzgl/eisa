# Blok Bileşen Sözleşmesi (`src/blocks/`)

Bu belge blok bileşenlerini yazan ajanlar/geliştiriciler için **bağlayıcıdır**. Veri şemaları için tek kaynak
`docs/web-sitesi/CONTRACT.md` §8 ve onun TypeScript karşılığı `src/lib/types.ts`'tir.

## 1. Dosya düzeni ve sahiplik

| Tip (API) | Dosya | Veri tipi | Not |
|---|---|---|---|
| `hero` | `hero.tsx` | `HeroVeri` | Sayfanın tek `h1`'i. Koyu zemin. |
| `sayfa_basligi` | `sayfa-basligi.tsx` | `SayfaBasligiVeri` | İç sayfaların tek `h1`'i. Koyu zemin. |
| `ozellik_kartlari` | `ozellik-kartlari.tsx` | `OzellikKartlariVeri` | `sutun` string gelebilir → `Number()` |
| `vurgu_bandi` | `vurgu-bandi.tsx` | `VurguBandiVeri` | `stil: kirmizi\|koyu\|acik` |
| `scroll_hikaye` | `scroll-hikaye.tsx` | `ScrollHikayeVeri` | Scroll-pin; reduced-motion'da statik liste |
| `surec_adimlari` | `surec-adimlari.tsx` | `SurecAdimlariVeri` | |
| `gorsel_metin` | `gorsel-metin.tsx` | `GorselMetinVeri` | `gorsel` null → dekoratif SVG/HTML illüstrasyon |
| `kazanc_hesaplayici` | `kazanc-hesaplayici.tsx` | `KazancHesaplayiciVeri` | Client adacığı; `uyari_notu` her zaman görünür |
| `sayaclar` | `sayaclar.tsx` | `SayaclarVeri` | `AnimatedCounter` |
| `logo_bandi` | `logo-bandi.tsx` | `LogoBandiVeri` | Boşsa `bos_mesaj` |
| `sss` | `sss.tsx` | `SssVeri` | FAQPage JSON-LD bu blokta (`JsonLd`) |
| `cta_banner` | `cta-banner.tsx` | `CtaBannerVeri` | `stil: koyu\|kirmizi` |
| `basvuru_formu` | `basvuru-formu.tsx` | `BasvuruFormuVeri` | Form mantığı `_parcalar/BasvuruFormIstemci.tsx` |
| `blog_son_yazilar` | `blog-son-yazilar.tsx` | `BlogSonYazilarVeri` | Async server component (`getSonYazilar`) |
| `ekip` | `ekip.tsx` | `EkipVeri` | `foto` null → baş harfli avatar |
| `zengin_metin` | `zengin-metin.tsx` | `ZenginMetinVeri` | `.prose-eisa` (+ `prose-eisa-genis`) |

- Her blok dosyası **default export** ile tek bir bileşen dışa aktarır. Dosya adını ve export biçimini değiştirmeyin
  (`index.tsx` haritası bunlara bağlıdır).
- Bir bloğa özel yardımcı bileşenler (client adacıkları, SVG illüstrasyonlar) `src/blocks/_parcalar/` altına,
  **blok adıyla başlayan** dosya adıyla konur (ör. `_parcalar/hero-kiosk.tsx`, `_parcalar/scroll-hikaye-istemci.tsx`).
  Böylece paralel çalışan ajanlar aynı dosyaya dokunmaz.
- **Ortak dosyalar** (`index.tsx`, `types.ts`, `src/components/**`, `src/lib/**`, `src/app/**`, `globals.css`)
  iskelet sahibinindir. Blok ajanları bunları değiştirmemelidir; gerçekten gerekiyorsa küçük, geriye uyumlu
  ekleme yapın ve son mesajınızda açıkça belirtin. `globals.css`'e blok özel stil eklemek yerine Tailwind
  utility'leri veya bileşen içi `style` kullanın.

## 2. Props

```ts
import type { BlokProps } from "./types";
export default function OzellikKartlari({ veri, blokId, anchorId, sira, ilk, sayfaSlug }: BlokProps<OzellikKartlariVeri>) { ... }
```

| Prop | Açıklama |
|---|---|
| `veri` | CONTRACT §8 `veri`. Opsiyonel (`?`) alanlar `""` veya `undefined` olabilir; listeler boş dizi olabilir. Her zaman savunmacı okuyun (`veri.kartlar?.length`). |
| `blokId` | Kalıcı anahtar (`"b_42"`). Benzersiz DOM id'leri buradan türetin: `${blokId}-baslik`. |
| `anchorId` | Yalnızca bilgi amaçlı. **Bloklar kök elemana `id={anchorId}` VERMEZ.** |
| `sira`, `ilk` | Sayfadaki sıra; `ilk` true ise LCP görsellerinde `priority` kullanın. |
| `sayfaSlug` | Bulunulan sayfa (`"anasayfa"`, `"teknoloji"` ...). |

## 3. Anchor kuralı (TEK KURAL)

`BlockRenderer` her bloğu şöyle sarar:

```html
<div id="{anchor_id}" data-blok-tip="ozellik_kartlari" [data-ilk-blok="koyu"]> <Blok .../> </div>
```

- Anchor `id`'si **her zaman bu sarmalayıcıdadır.** Menüdeki `/#pilot` gibi linkler bu id'ye kayar.
- `[id]` elemanlarının `scroll-margin-top` değeri globals.css'te header yüksekliğine göre ayarlıdır;
  JS kaydırması `lib/kaydirma.ts → hedefeKaydir()` ile header offset'li yapılır.
- Bloğun içinde ayrıca `id` gerekirse `blokId`'den türetin (ör. `aria-labelledby`).

## 4. Zemin, renk ve yerleşim

- Her blok kökte `<Section>` (`@/components/ui/Section`) kullanır: `arka_plan` (`acik|gri|koyu`), `padding`
  (`yok|kucuk|normal|buyuk`, varsayılan `normal`), `genislik` (`dar|orta|normal|genis`), `container`.
  Şemada `arka_plan` olan bloklar `arka_plan={veri.arka_plan}` verir; olmayanlar tasarımdaki sabit zemini seçer.
- Section `data-zemin` niteliği koyar; içerde **sabit renk yerine zemine duyarlı utility'leri** kullanın:
  `text-zemin-baslik`, `text-zemin-metin`, `text-zemin-soluk`, `text-zemin-vurgu`, `border-zemin-cizgi`,
  `bg-zemin-kart`. Böylece aynı blok açık/koyu zeminde doğru kontrastla görünür. `ButonLink`, `SectionHeading`
  ve odak halkaları zemine otomatik uyar.
- Tokenlar (CONTRACT §10): `bg-primary`, `bg-primary-aa` (beyaz metinli kırmızı yüzey, AA), `hover:bg-primary-hover`,
  `bg-dark`, `bg-dark-2`, `text-ink`, `text-muted`, `text-brand-deep`, `bg-bg`, `bg-card`, `border-line`, `bg-gri`;
  radius `rounded-kart`, `rounded-panel`, `rounded-buton`; gölge `shadow-kart`, `shadow-kart-hover`, `shadow-cta`,
  `shadow-koyu`; font `font-display` (Space Grotesk, başlıklar zaten öyle), `font-sans` (Inter);
  ease `ease-eisa`; yardımcılar `eyebrow`, `metin-gradyan`, `cam`, `cam-koyu`, `doku-izgara`, `doku-noise`;
  animasyonlar `animate-marquee` (`--marquee-sure`), `animate-yuzme`, `animate-nabiz`, `animate-yavas-don`, `animate-parilti`.
- Koyu üst bloklar (`hero`, `sayfa_basligi`) üstte `pt-[calc(var(--header-yukseklik)+var(--onizleme-bant)+4rem)]`
  boşluğu bırakır (header şeffaf olarak üstüne biner). Sayfa bu bloklardan biriyle başlamıyorsa `[[...slug]]/page.tsx`
  içeriği header yüksekliği kadar aşağı iter — bloklar bununla uğraşmaz.

## 5. Başlık hiyerarşisi ve erişilebilirlik

- Sayfa başına **tek `h1`**: yalnızca `hero` ve `sayfa_basligi`. Diğer bloklar `h2` (bölüm) / `h3` (kart) kullanır.
- `<Section aria-labelledby={baslikId}>` + `SectionHeading baslikId={baslikId}` deseni kullanılır (başlık yoksa vermeyin).
- İkon-only butonlarda `aria-label`; dekoratif SVG/ikonlarda `aria-hidden`. `Icon` bileşeni `etiket` verilmezse dekoratiftir.
- Etkileşimli öğeler klavye ile kullanılabilir olmalı; görünür odak halkasını kaldırmayın.
- Kontrast AA: küçük kırmızı metin için `text-zemin-vurgu` / `text-primary-hover`, beyaz yazılı kırmızı yüzey için `bg-primary-aa`.

## 6. Server / client ayrımı

- Bloklar **varsayılan olarak Server Component**'tir (dosyanın başında `"use client"` YOK).
- Animasyon/etkileşim gereken kısımlar küçük client adacıklarına ayrılır (`_parcalar/<blok>-*.tsx`, `"use client"`),
  blok dosyası bunları veriyle çağırır. Bütün bloğu client yapmayın.
- Veri isteyen bloklar `async` server component olabilir (`blog_son_yazilar`, `basvuru_formu` → `getSite()`).
  `@/lib/api` yalnızca sunucuda kullanılabilir (`server-only`). Client tarafında medya URL'si için `useMediaUrl()`,
  site ayarları için `useSite()` (`@/components/SiteProvider`) kullanın.
- Phosphor ikonları **tekil** import edilir: `import { XIcon } from "@phosphor-icons/react/dist/ssr/X"` (barrel import yok).
  CMS'ten gelen ikon adları için `<Icon ad={k.ikon} />` kullanın (48 ikon haritalı, bilinmeyen → `Sparkle`).

## 7. Animasyon kuralları

- Kütüphane: `motion` (`import { motion } from "motion/react"`) + Lenis (global, `SmoothScroll`). Easing: `EASE_EISA`
  (`@/lib/hareket`), süreler `SURE`, yaylar `YAY`.
- Giriş animasyonları için hazır primitifler: `Reveal` (tek öğe), `Stagger` + `StaggerItem` (listeler). Server component
  içinden kullanılabilirler; `once: true` ve reduced-motion uyumludur.
- `prefers-reduced-motion` açıkken: scroll-pin, parallax, sürekli/döngüsel animasyonlar (canvas, kiosk döngüsü, marquee)
  **kapanır** ve içerik statik, tam okunur hâlde gösterilir. Client'ta `useAzHareket()` (`@/lib/hooks`) kullanın.
- `requestAnimationFrame` / canvas döngüleri görünür değilken (IntersectionObserver, `document.hidden`) durmalı.
- Mıknatıs etkisi `MagneticButton` (yalnızca `pointer: fine`); sayaç `AnimatedCounter` (tr-TR biçim).
- Hidrasyon uyumu: sunucu ve istemcinin ilk render'ı aynı olmalı; `window`/`matchMedia` okumalarını effect veya
  `useSyncExternalStore` (hooks.ts) ile yapın.

## 8. Hazır primitifler (`@/components/ui/*`)

| Bileşen | Kullanım |
|---|---|
| `Container` | `genislik: dar\|orta\|normal\|genis` (Section zaten sarar) |
| `Section` | Bkz. §4 |
| `SectionHeading` | `ust_baslik`, `baslik`, `vurgu`, `aciklama`, `hizalama: sol\|orta`, `seviye`, `baslikId`, `boyut`, `animasyon` |
| `Reveal`, `Stagger`, `StaggerItem` | `as`, `yon`, `gecikme`, `sure`, `esik` |
| `ButonLink`, `ButonGrubu`, `butonSiniflari()` | CONTRACT `Buton` → link; anchor/dış link kuralları otomatik |
| `AkilliLink` | Düz link: iç → next/link, `#x`/`/#x` → offset'li kaydırma, dış → `target=_blank rel` |
| `Icon` | `ad`, `boyut`, `weight` (varsayılan duotone), `etiket` |
| `MediaImage` | `medya` (MediaRef\|null), `fill`, `sizes`, `priority`; null → `children` (yedek) |
| `Paragraflar` | `uzun_metin` → `<p>`'ler |
| `AnimatedCounter` | `deger`, `onek`, `sonek`, `ondalik` |
| `MagneticButton` | Sarmalayıcı |
| `GradientBackdrop`, `NoiseOverlay` (`Dekor.tsx`) | Dekoratif zemin katmanları |
| `JsonLd` (`@/components/JsonLd`) | Yapısal veri |

Yardımcılar (`@/lib/utils`): `cn`, `paragraflaraBol`, `vurguParcala`, `sayiFormatla`, `paraFormatla`, `tarihFormatla`, `slugYolu`.

## 9. İçerik ve hukuki ton

- e-isa doktor/teşhis sistemi değildir; tedavi veya kesin sonuç vaadi yok. Marka değil **kategori** önerir;
  **son karar eczacıdadır**. Kazanç rakamları "örnek senaryo / potansiyel"dir (garanti değil) — kazanç hesaplayıcıda
  `uyari_notu` her zaman görünür olmalıdır.
- Kullanıcıya görünen tüm sabit metinler Türkçe ve doğru Türkçe karakterlerle yazılır. İçerik CMS'ten gelir;
  bileşen içine sabit pazarlama metni gömmeyin (yalnızca boş durum, erişilebilirlik etiketleri vb.).

## 10. Hata dayanıklılığı

- `BlockRenderer` bilinmeyen tipi veya `veri`si olmayan bloğu atlar ve `console.warn` yazar; sayfa çökmez.
- Blok kendi içinde de eksik alanlara dayanıklı olmalı: boş liste → bölümü gizle veya boş durum göster; `null` medya → yedek.
- Veri isteyen bloklar hata fırlatmamalı (`getSonYazilar` zaten `[]` döner) — içerik yoksa `null` döndürüp kendini gizler.

## 11. Doğrulama

Bloklar MOCK modunda geliştirilir; tüm 16 tip `src/lib/mock/sayfalar.ts` içinde en az bir sayfada vardır:

```powershell
$env:MOCK_API = "1"; $env:NEXT_DIST_DIR = ".next-<ajan>"; npx next dev -p 30xx
```

Teslim öncesi: `npm run lint`, `npx tsc --noEmit` ve `MOCK_API=1` ile `npm run build` hatasız geçmelidir.
