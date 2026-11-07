/**
 * Web sitesi ikon kümesi — CONTRACT §2 "İkon" listesi ile BİREBİR aynıdır.
 * Backend `secim` seçenekleri ve site ikon haritası bu listeyi kullanır.
 *
 * İkonlar tek tek import edilir (barrel import'tan kaçınılır; tree-shaking).
 * `etiketler`: Türkçe arama kolaylığı için anahtar kelimeler.
 */
import {
  PhSparkle, PhBrain, PhShieldCheck, PhPackage, PhClockCounterClockwise, PhTimer,
  PhCheckCircle, PhUserCircle, PhUsers, PhStorefront, PhQrCode, PhReceipt,
  PhChartLineUp, PhTrendUp, PhCoins, PhCurrencyCircleDollar, PhDevices, PhDeviceMobile,
  PhMonitor, PhCloud, PhCloudArrowUp, PhWifiSlash, PhLightning, PhHeart, PhHeartbeat,
  PhFirstAidKit, PhPill, PhFlask, PhLeaf, PhMoon, PhLock, PhHandshake, PhTarget,
  PhMegaphone, PhLightbulb, PhRocket, PhGear, PhCpu, PhEye, PhChatCircleText,
  PhEnvelope, PhPhone, PhMapPin, PhStar, PhMedal, PhArrowsClockwise, PhPlant, PhSmiley,
} from '@phosphor-icons/vue';

export const VARSAYILAN_IKON = 'Sparkle';

export const WEBSITE_IKONLARI = [
  { ad: 'Sparkle', bilesen: PhSparkle, etiketler: 'parıltı yıldız yapay zeka' },
  { ad: 'Brain', bilesen: PhBrain, etiketler: 'beyin zeka akıl' },
  { ad: 'ShieldCheck', bilesen: PhShieldCheck, etiketler: 'kalkan güvenlik onay' },
  { ad: 'Package', bilesen: PhPackage, etiketler: 'paket kutu ürün' },
  { ad: 'ClockCounterClockwise', bilesen: PhClockCounterClockwise, etiketler: 'saat geçmiş geri' },
  { ad: 'Timer', bilesen: PhTimer, etiketler: 'zamanlayıcı süre kronometre' },
  { ad: 'CheckCircle', bilesen: PhCheckCircle, etiketler: 'onay tamam tik' },
  { ad: 'UserCircle', bilesen: PhUserCircle, etiketler: 'kullanıcı kişi profil' },
  { ad: 'Users', bilesen: PhUsers, etiketler: 'kullanıcılar ekip grup' },
  { ad: 'Storefront', bilesen: PhStorefront, etiketler: 'mağaza eczane dükkan' },
  { ad: 'QrCode', bilesen: PhQrCode, etiketler: 'qr kod karekod' },
  { ad: 'Receipt', bilesen: PhReceipt, etiketler: 'fiş reçete fatura' },
  { ad: 'ChartLineUp', bilesen: PhChartLineUp, etiketler: 'grafik artış analiz' },
  { ad: 'TrendUp', bilesen: PhTrendUp, etiketler: 'trend yükseliş artış' },
  { ad: 'Coins', bilesen: PhCoins, etiketler: 'para bozuk kazanç' },
  { ad: 'CurrencyCircleDollar', bilesen: PhCurrencyCircleDollar, etiketler: 'para döviz gelir' },
  { ad: 'Devices', bilesen: PhDevices, etiketler: 'cihazlar ekran' },
  { ad: 'DeviceMobile', bilesen: PhDeviceMobile, etiketler: 'telefon mobil cep' },
  { ad: 'Monitor', bilesen: PhMonitor, etiketler: 'ekran monitör kiosk' },
  { ad: 'Cloud', bilesen: PhCloud, etiketler: 'bulut' },
  { ad: 'CloudArrowUp', bilesen: PhCloudArrowUp, etiketler: 'bulut yükleme senkron' },
  { ad: 'WifiSlash', bilesen: PhWifiSlash, etiketler: 'çevrimdışı internet yok offline' },
  { ad: 'Lightning', bilesen: PhLightning, etiketler: 'şimşek hızlı enerji' },
  { ad: 'Heart', bilesen: PhHeart, etiketler: 'kalp sevgi sağlık' },
  { ad: 'Heartbeat', bilesen: PhHeartbeat, etiketler: 'nabız kalp atışı sağlık' },
  { ad: 'FirstAidKit', bilesen: PhFirstAidKit, etiketler: 'ilk yardım çanta sağlık' },
  { ad: 'Pill', bilesen: PhPill, etiketler: 'hap ilaç takviye' },
  { ad: 'Flask', bilesen: PhFlask, etiketler: 'şişe laboratuvar deney' },
  { ad: 'Leaf', bilesen: PhLeaf, etiketler: 'yaprak doğal bitkisel' },
  { ad: 'Moon', bilesen: PhMoon, etiketler: 'ay uyku gece' },
  { ad: 'Lock', bilesen: PhLock, etiketler: 'kilit gizlilik kvkk' },
  { ad: 'Handshake', bilesen: PhHandshake, etiketler: 'el sıkışma iş birliği ortaklık' },
  { ad: 'Target', bilesen: PhTarget, etiketler: 'hedef' },
  { ad: 'Megaphone', bilesen: PhMegaphone, etiketler: 'megafon duyuru kampanya' },
  { ad: 'Lightbulb', bilesen: PhLightbulb, etiketler: 'ampul fikir' },
  { ad: 'Rocket', bilesen: PhRocket, etiketler: 'roket başlangıç hızlı' },
  { ad: 'Gear', bilesen: PhGear, etiketler: 'dişli ayar' },
  { ad: 'Cpu', bilesen: PhCpu, etiketler: 'işlemci teknoloji' },
  { ad: 'Eye', bilesen: PhEye, etiketler: 'göz görünürlük' },
  { ad: 'ChatCircleText', bilesen: PhChatCircleText, etiketler: 'sohbet mesaj konuşma' },
  { ad: 'Envelope', bilesen: PhEnvelope, etiketler: 'zarf e-posta mail' },
  { ad: 'Phone', bilesen: PhPhone, etiketler: 'telefon arama' },
  { ad: 'MapPin', bilesen: PhMapPin, etiketler: 'konum harita adres' },
  { ad: 'Star', bilesen: PhStar, etiketler: 'yıldız favori' },
  { ad: 'Medal', bilesen: PhMedal, etiketler: 'madalya ödül' },
  { ad: 'ArrowsClockwise', bilesen: PhArrowsClockwise, etiketler: 'yenile döngü tekrar' },
  { ad: 'Plant', bilesen: PhPlant, etiketler: 'bitki büyüme' },
  { ad: 'Smiley', bilesen: PhSmiley, etiketler: 'gülen yüz memnun' },
];

export const IKON_ADLARI = WEBSITE_IKONLARI.map((i) => i.ad);

const _harita = Object.fromEntries(WEBSITE_IKONLARI.map((i) => [i.ad, i.bilesen]));

/** İkon adından bileşen; bilinmeyen ad için Sparkle (site ile aynı davranış). */
export function ikonBileseni(ad) {
  return _harita[ad] || PhSparkle;
}
