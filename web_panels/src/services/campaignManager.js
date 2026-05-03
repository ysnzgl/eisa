/**
 * Kampanya Yönetimi Servisi — DOOH Idle-Screen Reklam Sistemi
 *
 * Mock implementasyon. Gerçek endpoint'ler:
 *   GET    /api/campaigns/
 *   POST   /api/campaigns/
 *   PATCH  /api/campaigns/{id}/
 *   DELETE /api/campaigns/{id}/
 *   POST   /api/campaigns/media-upload/  (multipart/form-data)
 *   GET    /api/pharmacies/              (targeting için)
 */
import { http } from './api';

// ─── Sabitler ─────────────────────────────────────────────────────────────────
export const TR_PROVINCES = [
  'Adana','Adıyaman','Afyonkarahisar','Ağrı','Aksaray','Amasya','Ankara','Antalya',
  'Ardahan','Artvin','Aydın','Balıkesir','Bartın','Batman','Bayburt','Bilecik',
  'Bingöl','Bitlis','Bolu','Burdur','Bursa','Çanakkale','Çankırı','Çorum',
  'Denizli','Diyarbakır','Düzce','Edirne','Elazığ','Erzincan','Erzurum','Eskişehir',
  'Gaziantep','Giresun','Gümüşhane','Hakkari','Hatay','Iğdır','Isparta','İstanbul',
  'İzmir','Kahramanmaraş','Karabük','Karaman','Kars','Kastamonu','Kayseri','Kırıkkale',
  'Kırklareli','Kırşehir','Kilis','Kocaeli','Konya','Kütahya','Malatya','Manisa',
  'Mardin','Mersin','Muğla','Muş','Nevşehir','Niğde','Ordu','Osmaniye','Rize',
  'Sakarya','Samsun','Siirt','Sinop','Sivas','Şanlıurfa','Şırnak','Tekirdağ',
  'Tokat','Trabzon','Tunceli','Uşak','Van','Yalova','Yozgat','Zonguldak',
];

export const MOCK_PHARMACIES = [
  { id: 1, name: 'Merkez Eczanesi',  province: 'İstanbul' },
  { id: 2, name: 'Güneş Eczanesi',   province: 'Ankara'   },
  { id: 3, name: 'Sağlık Eczanesi',  province: 'İzmir'    },
  { id: 4, name: 'Yıldız Eczanesi',  province: 'Bursa'    },
  { id: 5, name: 'Hayat Eczanesi',   province: 'Antalya'  },
  { id: 6, name: 'Umut Eczanesi',    province: 'Konya'    },
  { id: 7, name: 'Şifa Eczanesi',    province: 'Adana'    },
  { id: 8, name: 'Nur Eczanesi',     province: 'Gaziantep'},
];

// ─── Mock Kampanya Verisi ─────────────────────────────────────────────────────
const _now = Date.now();
const _d = (offsetDays) => new Date(_now + offsetDays * 86400000).toISOString();

let _campaigns = [
  {
    id: 1,
    name: 'Bahar Vitamin Kampanyası',
    client: 'Eczacıbaşı Sağlık',
    media_url: 'https://placehold.co/1080x1920/1a1a2e/ff6b35?text=Vitamin+Reklam',
    media_type: 'image',
    duration_sec: 15,
    starts_at: _d(-5),
    ends_at: _d(25),
    broadcast_start: '08:00',
    broadcast_end: '20:00',
    target_provinces: ['İstanbul', 'Ankara', 'İzmir'],
    target_pharmacy_ids: [],
    is_active: true,
    created_at: _d(-10),
  },
  {
    id: 2,
    name: 'Yazlık Güneş Kremi Tanıtımı',
    client: 'Dermamed A.Ş.',
    media_url: 'https://placehold.co/1080x1920/0f3460/e94560?text=Güneş+Kremi',
    media_type: 'image',
    duration_sec: 10,
    starts_at: _d(3),
    ends_at: _d(33),
    broadcast_start: '10:00',
    broadcast_end: '18:00',
    target_provinces: ['Antalya', 'Muğla', 'İzmir'],
    target_pharmacy_ids: [5],
    is_active: true,
    created_at: _d(-3),
  },
  {
    id: 3,
    name: 'Kış Grip Aşısı Hatırlatma',
    client: 'Sağlık Bakanlığı İletişim',
    media_url: 'https://placehold.co/1080x1920/16213e/0f3460?text=Grip+Aşısı',
    media_type: 'image',
    duration_sec: 20,
    starts_at: _d(15),
    ends_at: _d(75),
    broadcast_start: '00:00',
    broadcast_end: '23:59',
    target_provinces: [],
    target_pharmacy_ids: [],
    is_active: true,
    created_at: _d(-1),
  },
  {
    id: 4,
    name: 'Prebiyotik Destek Serisi',
    client: 'BioFlora İlaç',
    media_url: 'https://placehold.co/1080x1920/2d6a4f/52b788?text=Prebiyotik',
    media_type: 'image',
    duration_sec: 12,
    starts_at: _d(-45),
    ends_at: _d(-3),
    broadcast_start: '09:00',
    broadcast_end: '21:00',
    target_provinces: ['Bursa', 'Konya', 'Adana'],
    target_pharmacy_ids: [4, 6, 7],
    is_active: false,
    created_at: _d(-50),
  },
  {
    id: 5,
    name: 'Kolesterol İzleme Programı',
    client: 'Cardio Med',
    media_url: 'https://placehold.co/1080x1920/3a0ca3/7209b7?text=Kolesterol',
    media_type: 'image',
    duration_sec: 18,
    starts_at: _d(-90),
    ends_at: _d(-30),
    broadcast_start: '07:00',
    broadcast_end: '19:00',
    target_provinces: ['Gaziantep', 'Diyarbakır'],
    target_pharmacy_ids: [8],
    is_active: false,
    created_at: _d(-95),
  },
];

let _idSeq = 10;

function _delay(ms = 380) {
  return new Promise((r) => setTimeout(r, ms));
}

function _clone(v) {
  return JSON.parse(JSON.stringify(v));
}

// ─── Servis Fonksiyonları ─────────────────────────────────────────────────────

/**
 * Tüm kampanyaları getirir.
 * Gerçek API: return http.get('/api/campaigns/').then(r => r.data);
 */
export async function getCampaigns() {
  await _delay();
  return _clone(_campaigns);
}

/**
 * Yeni kampanya oluşturur.
 * Gerçek API: return http.post('/api/campaigns/', data).then(r => r.data);
 */
export async function createCampaign(data) {
  await _delay();
  const camp = { id: _idSeq++, created_at: new Date().toISOString(), ...data };
  _campaigns.unshift(camp);
  return _clone(camp);
}

/**
 * Kampanyayı günceller.
 * Gerçek API: return http.patch(`/api/campaigns/${id}/`, data).then(r => r.data);
 */
export async function updateCampaign(id, data) {
  await _delay();
  const idx = _campaigns.findIndex((c) => c.id === id);
  if (idx === -1) throw new Error('Kampanya bulunamadı');
  Object.assign(_campaigns[idx], data);
  return _clone(_campaigns[idx]);
}

/**
 * Kampanyayı siler.
 * Gerçek API: return http.delete(`/api/campaigns/${id}/`);
 */
export async function deleteCampaign(id) {
  await _delay();
  _campaigns = _campaigns.filter((c) => c.id !== id);
}

/**
 * Medya yüklemeyi simüle eder.
 * Gerçek API:
 *   const fd = new FormData(); fd.append('file', file);
 *   return http.post('/api/campaigns/media-upload/', fd, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data.url);
 * @param {File} file
 * @returns {Promise<{ url: string, type: 'image'|'video' }>}
 */
export async function uploadMedia(file) {
  await new Promise((r) => setTimeout(r, 900 + Math.random() * 600));
  const type = file.type.startsWith('video') ? 'video' : 'image';
  // Mock: return an object URL for local preview
  const url = URL.createObjectURL(file);
  return { url, type };
}

// ─── Yardımcı ─────────────────────────────────────────────────────────────────

/**
 * Kampanyanın durumunu hesaplar.
 * @param {{ starts_at: string, ends_at: string }} c
 * @returns {'active'|'upcoming'|'ended'}
 */
export function campaignStatus(c) {
  const now = Date.now();
  const start = new Date(c.starts_at).getTime();
  const end   = new Date(c.ends_at).getTime();
  if (now < start) return 'upcoming';
  if (now > end)   return 'ended';
  return 'active';
}
