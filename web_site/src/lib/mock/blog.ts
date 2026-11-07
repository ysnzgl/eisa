/**
 * MOCK: blog — CONTRACT §9: 3 kategori, 3 yayınlanmış yazı (temkinli dil).
 */

import type { BlogDetay, BlogKategori, BlogOzet } from "../types";

export const mockKategoriler: BlogKategori[] = [
  { ad: "Sağlık Okuryazarlığı", slug: "saglik-okuryazarligi" },
  { ad: "Eczane Yönetimi", slug: "eczane-yonetimi" },
  { ad: "Duyurular", slug: "duyurular" },
];

const [saglik, eczane, duyuru] = mockKategoriler;

const YAZAR = "e-isa Ekibi";

export const mockBlogYazilari: BlogDetay[] = [
  {
    slug: "pilot-sureci-nasil-isler",
    baslik: "e-isa 1 aylık ücretsiz pilot süreci nasıl işler?",
    ozet:
      "Başvurudan kuruluma, veri takibinden değerlendirme toplantısına kadar 30 günlük ücretsiz pilot sürecin adımlarını özetledik.",
    kapak: null,
    kategori: duyuru,
    etiketler: ["pilot", "kurulum", "e-isa"],
    yazar_adi: YAZAR,
    yayin_tarihi: "2026-11-05T09:00:00Z",
    okuma_suresi: 4,
    seo: {
      baslik: "1 Aylık Ücretsiz Pilot Süreci Nasıl İşler?",
      aciklama: "e-isa pilot süreci: başvuru, kurulum, eğitim, izleme ve değerlendirme adımları.",
      og_gorsel: null,
    },
    icerik_html: `
<p>e-isa'yı eczanenizde denemek için herhangi bir ücret ödemeniz veya uzun vadeli bir taahhüde girmeniz gerekmez. Pilot sürecin amacı basit: e-isa'yı varsayımlarla değil, eczanenizin kendi verileriyle değerlendirmenizi sağlamak.</p>
<h2>1. Başvuru ve ön görüşme</h2>
<p>Sitemizdeki pilot başvuru formunu doldurduktan sonra ekibimiz sizinle iletişime geçer. Kısa bir ön görüşmede eczanenizin müşteri akışını, bekleme alanını ve beklentilerinizi konuşuruz.</p>
<h2>2. Kurulum</h2>
<p>Kompakt kiosk ünitesini bekleme alanında en uygun konuma yerleştiririz. Kurulum genellikle eczanenin günlük işleyişini aksatmadan, kısa sürede tamamlanır.</p>
<h2>3. Kısa eğitim</h2>
<p>Eczane ekibine QR / fiş akışını ve sonuçların nasıl değerlendirileceğini anlatırız. e-isa'nın ürettiği çıktı bir <strong>ön inceleme</strong>dir; son değerlendirme her zaman eczacıdadır.</p>
<h2>4. İzleme ve geri bildirim</h2>
<p>30 gün boyunca etkileşim sayısı, kategori dağılımı ve danışmanlık sürecine etkisi gibi göstergeleri birlikte izleriz. Saha ekibimiz süreç boyunca yanınızdadır.</p>
<h2>5. Değerlendirme</h2>
<p>Pilot sonunda verileri birlikte değerlendiririz. Devam edip etmeme kararı tamamen sizindir.</p>
<blockquote>Pilot süreçte paylaşılan rakamlar eczaneye özgüdür; başka eczaneler için garanti veya taahhüt niteliği taşımaz.</blockquote>
`.trim(),
    ilgili: [],
  },
  {
    slug: "durtme-yaklasimi-saglik-okuryazarligi",
    baslik: "Dürtme (nudge) yaklaşımı sağlık okuryazarlığına nasıl katkı sağlar?",
    ozet:
      "Davranışsal ekonomiden doğan dürtme yaklaşımı, kişiyi yönlendirmeden düşünmeye davet eder. Eczane ortamında bunun ne anlama geldiğine baktık.",
    kapak: null,
    kategori: saglik,
    etiketler: ["dürtme", "nudge", "sağlık okuryazarlığı"],
    yazar_adi: YAZAR,
    yayin_tarihi: "2026-10-28T09:00:00Z",
    okuma_suresi: 5,
    seo: {
      baslik: "Dürtme (Nudge) Yaklaşımı ve Sağlık Okuryazarlığı",
      aciklama: "Dürtme yaklaşımının eczane ortamında sağlık okuryazarlığına olası katkıları ve sınırları.",
      og_gorsel: null,
    },
    icerik_html: `
<p>Dürtme (nudge), davranışsal ekonomide kişinin seçim özgürlüğünü kısıtlamadan, karar ortamını sadeleştirerek daha bilinçli seçimler yapmasını kolaylaştıran yaklaşımların genel adıdır. Yasaklamaz, zorlamaz; yalnızca düşünmeye alan açar.</p>
<h2>Sağlık okuryazarlığı neden önemli?</h2>
<p>Sağlık okuryazarlığı, kişinin sağlıkla ilgili bilgiye ulaşma, onu anlama ve bu bilgiyle uygun sorular sorabilme becerisidir. Eczacısına doğru soruyu soran kişi, görüşmeden daha fazla fayda sağlar.</p>
<h2>Eczane ortamında dürtme ne demek?</h2>
<p>Reçete hazırlanırken geçen birkaç dakika, kişinin kendi ihtiyaçlarını düşünmesi için uygun bir andır. e-isa bu anda:</p>
<ul>
<li>karmaşık tıbbi terimler yerine yalın seçenekler sunar,</li>
<li>enerji, uyku, sindirim gibi gündelik başlıklarda kısa sorular sorar,</li>
<li>sonucu bir <strong>kategori</strong> olarak özetler ve eczacıya iletir.</li>
</ul>
<h2>Sınırları net çizmek</h2>
<p>Dürtme yaklaşımı bir teşhis aracı değildir ve tedavi önermez. e-isa da marka önermez; yalnızca eczacıyla yapılacak görüşmeye hazırlık niteliğinde bir kategori özeti üretir. Hangi ürünün kişiye uygun olduğuna, gerekiyorsa hekime yönlendirme yapılıp yapılmayacağına eczacı karar verir.</p>
<h2>Sonuç</h2>
<p>Doğru tasarlanmış küçük bir dijital etkileşim, kişinin eczacısıyla daha odaklı bir görüşme yapmasına yardımcı olabilir. Amaç satış baskısı değil, farkındalıktır.</p>
`.trim(),
    ilgili: [],
  },
  {
    slug: "recete-bekleme-suresi-firsat",
    baslik: "Reçete bekleme süresi eczane için neden bir fırsat?",
    ozet:
      "Reçete hazırlanırken geçen kısa bekleme süresi, doğru kurgulandığında hem müşteri deneyimi hem de eczacının danışmanlık rolü için değerli bir ana dönüşebilir.",
    kapak: null,
    kategori: eczane,
    etiketler: ["eczane yönetimi", "müşteri deneyimi"],
    yazar_adi: YAZAR,
    yayin_tarihi: "2026-10-20T09:00:00Z",
    okuma_suresi: 4,
    seo: {
      baslik: "Reçete Bekleme Süresi Eczane İçin Neden Bir Fırsat?",
      aciklama: "Eczanedeki bekleme süresini müşteri deneyimi ve danışmanlık açısından değerlendirmenin yolları.",
      og_gorsel: null,
    },
    icerik_html: `
<p>Eczaneye gelen pek çok kişi, reçetesi hazırlanırken birkaç dakika bekler. Bu süre çoğu zaman telefona bakarak ya da sırayı izleyerek geçer. Oysa bekleme anı, doğru kurgulandığında hem müşteri hem de eczane için anlamlı bir fırsattır.</p>
<h2>Sessiz müşteri</h2>
<p>Birçok kişi, eczacısına sormak istediği bir konuyu yoğunluk veya çekingenlik nedeniyle dile getirmez. Bekleme süresinde sunulan sade bir dijital etkileşim, bu kişilerin ihtiyaçlarını fark etmelerine ve görüşmeye hazırlıklı gelmelerine yardımcı olabilir.</p>
<h2>Eczacının danışmanlık rolü</h2>
<p>Kişi kendi ihtiyacını önceden düşündüğünde, eczacıyla yapılan görüşme daha kısa ve daha odaklı olabilir. Eczacı, bir kategori özetiyle başlayan görüşmede uzmanlığını daha etkin kullanır.</p>
<h2>Tamamlayıcı kategoriler</h2>
<p>Kısa sorulara verilen yanıtlar, yalnızca tek bir ihtiyaca değil, tamamlayıcı kategorilere de işaret edebilir. Bu da eczacının bütüncül bir danışmanlık sunmasını kolaylaştırır.</p>
<h2>Dikkat edilmesi gerekenler</h2>
<ul>
<li>Etkileşim kısa ve gönüllü olmalıdır.</li>
<li>Marka yönlendirmesi yapılmamalı, yalnızca kategori düzeyinde kalınmalıdır.</li>
<li>Son değerlendirme her zaman eczacıya bırakılmalıdır.</li>
</ul>
<p>Sepet ortalamasındaki olası değişim eczaneden eczaneye farklılık gösterir; bu nedenle en sağlıklı yöntem, kendi verilerinizle yapılan bir pilot değerlendirmedir.</p>
`.trim(),
    ilgili: [],
  },
];

/** BlogDetay → BlogOzet */
export function ozetle(y: BlogDetay): BlogOzet {
  return {
    slug: y.slug,
    baslik: y.baslik,
    ozet: y.ozet,
    kapak: y.kapak,
    kategori: y.kategori,
    etiketler: y.etiketler,
    yazar_adi: y.yazar_adi,
    yayin_tarihi: y.yayin_tarihi,
    okuma_suresi: y.okuma_suresi,
  };
}
