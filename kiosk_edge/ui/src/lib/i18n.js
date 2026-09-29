// Kiosk dil (i18n) altyapisi — Turkce (tr) + Ingilizce (en).
//
// - `language`: secili dil (localStorage 'kiosk_lang', varsayilan 'tr').
// - `t`: sabit metinler icin ceviri fonksiyonu store'u ($t('anahtar', {vars})).
// - `localize`: DB'den gelen dinamik icerik icin (ad/ad_en, metin/metin_en).
//
// Kullanim (Svelte):
//   import { t, localize, toggleLanguage } from '../lib/i18n.js';
//   <h2>{$t('welcome.title')}</h2>
//   <h3>{$localize(cat)}</h3>              // cat.ad / cat.ad_en
//   <p>{$localize(q, 'metin')}</p>         // q.metin / q.metin_en

import { derived, writable } from 'svelte/store';

const STORAGE_KEY = 'kiosk_lang';
export const SUPPORTED_LANGS = ['tr', 'en'];

function readInitialLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && SUPPORTED_LANGS.includes(saved)) return saved;
  } catch {
    /* localStorage erisilemez — varsayilana dus */
  }
  return 'tr';
}

export const language = writable(readInitialLang());

language.subscribe((lang) => {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* yut */
  }
  if (typeof document !== 'undefined' && document.documentElement) {
    document.documentElement.lang = lang;
  }
});

export function setLanguage(lang) {
  if (SUPPORTED_LANGS.includes(lang)) language.set(lang);
}

export function toggleLanguage() {
  language.update((v) => (v === 'tr' ? 'en' : 'tr'));
}

// ── Sabit metin sozlugu ──────────────────────────────────────────────────
const DICT = {
  tr: {
    'common.continue': 'Devam Et',
    'common.cancel': 'Vazgeç',
    'common.back': 'Geri',
    'common.loading': 'Yükleniyor...',
    'common.moreOptions': 'Daha fazla seçenek',
    'common.yes': 'EVET',
    'common.no': 'HAYIR',

    'welcome.title': 'Nasıl Yardımcı Olabilirim?',
    'welcome.flowA': 'Şikayetimi Seç & Soruları Cevapla',
    'welcome.flowASub': 'Size uygun takviye önerisini alın ve QR fişinizi oluşturun.',
    'welcome.or': 'VEYA',
    'welcome.flowConsult': 'Eczacınıza Özel Danışın',
    'welcome.flowConsultSub': 'Kişisel konularınızı gizlilik içinde paylaşabilirsiniz.',
    'welcome.footer': 'Bu sistem marka önermez. Verileriniz anonim tutulur.',

    'demo.step': 'Adım 1 / 3 — Hızlı Profil',
    'demo.title': 'Devam etmek için lütfen seçin',
    'demo.ageLabel': 'Yaş Aralığınız',
    'demo.sexLabel': 'Cinsiyetiniz',
    'demo.female': 'Kadın',
    'demo.male': 'Erkek',

    'category.step': 'Adım 2 / 3 — Şikayet Seçimi',
    'category.title': 'Şikayet türünüzü seçin',
    'category.subTitle': '{name} — alt başlık seçin',
    'category.loading': 'Kategoriler yükleniyor…',
    'category.empty': 'Bu başlık altında kategori bulunamadı.',

    'consult.subtitle': 'Eczacınıza Danışın',
    'consult.title': 'Danışma konunuzu seçin',
    'consult.empty': 'Danışma kategorisi tanımlanmamış.',

    'question.step': 'Adım 3 / 3',
    'question.loading': 'Sorular yükleniyor...',
    'question.prev': 'Önceki Soru',

    'result.recommendationLabel': 'Önerilen Etken Maddeler — {name}',
    'result.consultLabel': 'Danışma talebi gönderildi',
    'result.consultSub': 'Eczacınız sizi bekliyor — QR kodu okutunuz.',
    'result.oneOnScreen': 'Bir seçenek ekranda, diğerleri eczacınızda!',
    'result.otherIngredients': 'Diğer etken maddeler için tıklayınız',
    'result.qrHeading': 'Lütfen Fişinizi/QR kodunuzu Eczacınıza gösterin.',
    'result.qrFailed': 'QR kodu oluşturulamadı. Lütfen eczacıya danışın.',
    'result.qrNote': 'Öneriler için profesyonellere danışın. Yapay zeka tarafından üretilmiş yanıtlarda hata olabilir.',
    'result.receiptPreview': 'Termal fiş önizlemesi',
    'result.receiptHealthy': 'Sağlıklı günler diler',
    'result.receiptQrNote': '— QR kodu yazıcıdan çıkar —',
    'result.newComplaint': 'Başka Bir Şikayet Seç',
    'result.home': 'Ana Sayfaya Dön',
    'result.syncWarn': 'Sunucuya henüz gönderilemedi',

    'idleCountdown.title': 'İşleminiz devam ediyor mu?',
    'idleCountdown.body': 'İşleminiz {n} saniye içinde ana ekrana dönecek.',
    'idleCountdown.continue': 'Devam Et',
    'idleCountdown.return': 'Ana ekrana dön',

    'idle.cta': 'SİZE UYGUN ÖNERİLER İÇİN',
    'idle.touch': 'DOKUNUN',
    'idle.welcome': 'HOŞGELDİNİZ',
    'idle.defaultPharmacy': 'Eczanemize',
    'idle.sponsorTitle': 'Bu Alana Sponsor Olabilirsiniz',
    'idle.sponsorSub': 'Sponsorluk Ağı · Eczane Ekranında Markanız',

    'wifi.connectionSetup': 'Bağlantı kurulumu',
    'wifi.headerSubtitle': 'Devam etmek için kullanmak istediğiniz Wi-Fi ağını seçin.',
    'wifi.availableNetworks': 'Kullanılabilir ağlar',
    'wifi.scanning': 'Yakındaki ağlar aranıyor…',
    'wifi.networksFound': '{n} ağ bulundu',
    'wifi.rescan': 'Ağları yeniden tara',
    'wifi.scanningTitle': 'Ağlar taranıyor',
    'wifi.scanningHint': 'Lütfen kısa bir süre bekleyin.',
    'wifi.retry': 'Tekrar dene',
    'wifi.noNetworks': 'Çevrede Wi-Fi ağı bulunamadı.',
    'wifi.scanFailed': 'Ağ taraması başarısız oldu.',
    'wifi.selectedNetwork': 'Seçili ağ',
    'wifi.secured': 'Şifreli',
    'wifi.open': 'Açık ağ',
    'wifi.passwordPlaceholder': 'Wi-Fi şifresini girin',
    'wifi.connect': 'Bağlan',
    'wifi.connecting': 'Bağlanıyor…',
    'wifi.noPasswordNeeded': 'Bu ağ parola istemiyor. Bağlanarak devam edebilirsiniz.',
    'wifi.connectingState': 'Bağlantı kuruluyor…',
    'wifi.doConnect': 'Ağa bağlan',
    'wifi.passwordHint': 'Ağ parolanız yalnızca bağlantı kurulurken kullanılır.',
    'wifi.connectFailed': 'Bağlantı kurulamadı. Şifreyi kontrol edin.',

    'lang.switchTo': 'English',
  },
  en: {
    'common.continue': 'Continue',
    'common.cancel': 'Cancel',
    'common.back': 'Back',
    'common.loading': 'Loading...',
    'common.moreOptions': 'More options',
    'common.yes': 'YES',
    'common.no': 'NO',

    'welcome.title': 'How Can I Help You?',
    'welcome.flowA': 'Select My Complaint & Answer Questions',
    'welcome.flowASub': 'Get a supplement suggestion suited to you and create your QR receipt.',
    'welcome.or': 'OR',
    'welcome.flowConsult': 'Consult Your Pharmacist Privately',
    'welcome.flowConsultSub': 'You can share your personal matters in confidence.',
    'welcome.footer': 'This system does not recommend brands. Your data is kept anonymous.',

    'demo.step': 'Step 1 / 3 — Quick Profile',
    'demo.title': 'Please make a selection to continue',
    'demo.ageLabel': 'Your Age Range',
    'demo.sexLabel': 'Your Gender',
    'demo.female': 'Female',
    'demo.male': 'Male',

    'category.step': 'Step 2 / 3 — Complaint Selection',
    'category.title': 'Select your type of complaint',
    'category.subTitle': '{name} — select a subcategory',
    'category.loading': 'Loading categories…',
    'category.empty': 'No category found under this heading.',

    'consult.subtitle': 'Consult Your Pharmacist',
    'consult.title': 'Select your consultation topic',
    'consult.empty': 'No consultation category defined.',

    'question.step': 'Step 3 / 3',
    'question.loading': 'Loading questions...',
    'question.prev': 'Previous Question',

    'result.recommendationLabel': 'Recommended Active Ingredients — {name}',
    'result.consultLabel': 'Consultation request sent',
    'result.consultSub': 'Your pharmacist is waiting for you — please scan the QR code.',
    'result.oneOnScreen': 'One option on the screen, the rest at your pharmacist!',
    'result.otherIngredients': 'Click for other active ingredients',
    'result.qrHeading': 'Please show your receipt/QR code to your pharmacist.',
    'result.qrFailed': 'QR code could not be created. Please consult the pharmacist.',
    'result.qrNote': 'Consult professionals for recommendations. AI-generated responses may contain errors.',
    'result.receiptPreview': 'Thermal receipt preview',
    'result.receiptHealthy': 'Wishing you healthy days',
    'result.receiptQrNote': '— QR code prints from the printer —',
    'result.newComplaint': 'Select Another Complaint',
    'result.home': 'Return to Home',
    'result.syncWarn': 'Not yet sent to the server',

    'idleCountdown.title': 'Is your session still active?',
    'idleCountdown.body': 'Your session will return to the home screen in {n} seconds.',
    'idleCountdown.continue': 'Continue',
    'idleCountdown.return': 'Return to home screen',

    'idle.cta': 'FOR SUGGESTIONS SUITED TO YOU',
    'idle.touch': 'TOUCH',
    'idle.welcome': 'WELCOME',
    'idle.defaultPharmacy': 'Our Pharmacy',
    'idle.sponsorTitle': 'You Can Sponsor This Space',
    'idle.sponsorSub': 'Sponsorship Network · Your Brand on the Pharmacy Screen',

    'wifi.connectionSetup': 'Connection setup',
    'wifi.headerSubtitle': 'Select the Wi-Fi network you want to use to continue.',
    'wifi.availableNetworks': 'Available networks',
    'wifi.scanning': 'Searching for nearby networks…',
    'wifi.networksFound': '{n} networks found',
    'wifi.rescan': 'Rescan networks',
    'wifi.scanningTitle': 'Scanning networks',
    'wifi.scanningHint': 'Please wait a moment.',
    'wifi.retry': 'Try again',
    'wifi.noNetworks': 'No Wi-Fi network found nearby.',
    'wifi.scanFailed': 'Network scan failed.',
    'wifi.selectedNetwork': 'Selected network',
    'wifi.secured': 'Secured',
    'wifi.open': 'Open network',
    'wifi.passwordPlaceholder': 'Enter the Wi-Fi password',
    'wifi.connect': 'Connect',
    'wifi.connecting': 'Connecting…',
    'wifi.noPasswordNeeded': 'This network requires no password. You can continue by connecting.',
    'wifi.connectingState': 'Establishing connection…',
    'wifi.doConnect': 'Connect to network',
    'wifi.passwordHint': 'Your network password is used only while connecting.',
    'wifi.connectFailed': 'Could not connect. Please check the password.',

    'lang.switchTo': 'Türkçe',
  },
};

function interpolate(str, vars) {
  if (!vars) return str;
  let out = str;
  for (const [k, v] of Object.entries(vars)) {
    out = out.split(`{${k}}`).join(String(v));
  }
  return out;
}

export const t = derived(language, ($lang) => (key, vars) => {
  const table = DICT[$lang] ?? DICT.tr;
  const value = table[key] ?? DICT.tr[key] ?? key;
  return interpolate(value, vars);
});

// DB icerigi icin dil secici: en secili ve `${base}_en` doluysa onu, aksi
// halde Turkce `base` alanini dondurur.
export const localize = derived(language, ($lang) => (obj, base = 'ad') => {
  if (!obj) return '';
  if ($lang === 'en') {
    const en = obj[`${base}_en`];
    if (en != null && String(en).trim() !== '') return en;
  }
  return obj[base] ?? '';
});
