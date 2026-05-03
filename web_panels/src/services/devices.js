/**
 * Cihaz Yönetimi Servisi — Eczane & Kiosk
 *
 * Mock implementasyon: Gerçek API çağrısı için yorum satırları kaldırılabilir.
 * Gerçek endpoint'ler:
 *   GET    /api/pharmacies/
 *   POST   /api/pharmacies/
 *   PATCH  /api/pharmacies/{id}/
 *   DELETE /api/pharmacies/{id}/
 *   GET    /api/pharmacies/kiosk-status/
 */
import { http } from './api';

// ─── Mock Veri ───────────────────────────────────────────────────────────────
const _pharmacies = [
  { id: 1, name: 'Merkez Eczanesi',    province: 'İstanbul', district: 'Kadıköy',    owner: 'Ahmet Yılmaz',   kioskCount: 3 },
  { id: 2, name: 'Güneş Eczanesi',     province: 'Ankara',   district: 'Çankaya',    owner: 'Fatma Kaya',     kioskCount: 2 },
  { id: 3, name: 'Sağlık Eczanesi',    province: 'İzmir',    district: 'Konak',      owner: 'Mehmet Demir',   kioskCount: 1 },
  { id: 4, name: 'Yıldız Eczanesi',    province: 'Bursa',    district: 'Osmangazi',  owner: 'Zeynep Çelik',   kioskCount: 2 },
  { id: 5, name: 'Hayat Eczanesi',     province: 'Antalya',  district: 'Muratpaşa',  owner: 'Ali Şahin',      kioskCount: 1 },
  { id: 6, name: 'Umut Eczanesi',      province: 'Konya',    district: 'Selçuklu',   owner: 'Ayşe Arslan',    kioskCount: 2 },
  { id: 7, name: 'Şifa Eczanesi',      province: 'Adana',    district: 'Seyhan',     owner: 'Hasan Kılıç',    kioskCount: 2 },
  { id: 8, name: 'Nur Eczanesi',       province: 'Gaziantep',district: 'Şahinbey',   owner: 'Emine Öztürk',   kioskCount: 1 },
];

const _now = () => Date.now();
const _minsAgo = (m) => new Date(_now() - m * 60 * 1000).toISOString();

const _kiosks = [
  { id: 'KSK-001', pharmacyId: 1, pharmacyName: 'Merkez Eczanesi',  lastPing: _minsAgo(2)   },
  { id: 'KSK-002', pharmacyId: 1, pharmacyName: 'Merkez Eczanesi',  lastPing: _minsAgo(7)   },
  { id: 'KSK-003', pharmacyId: 1, pharmacyName: 'Merkez Eczanesi',  lastPing: _minsAgo(45)  },
  { id: 'KSK-004', pharmacyId: 2, pharmacyName: 'Güneş Eczanesi',   lastPing: _minsAgo(1)   },
  { id: 'KSK-005', pharmacyId: 2, pharmacyName: 'Güneş Eczanesi',   lastPing: _minsAgo(120) },
  { id: 'KSK-006', pharmacyId: 3, pharmacyName: 'Sağlık Eczanesi',  lastPing: _minsAgo(5)   },
  { id: 'KSK-007', pharmacyId: 4, pharmacyName: 'Yıldız Eczanesi',  lastPing: _minsAgo(3)   },
  { id: 'KSK-008', pharmacyId: 4, pharmacyName: 'Yıldız Eczanesi',  lastPing: _minsAgo(240) },
  { id: 'KSK-009', pharmacyId: 5, pharmacyName: 'Hayat Eczanesi',   lastPing: _minsAgo(8)   },
  { id: 'KSK-010', pharmacyId: 6, pharmacyName: 'Umut Eczanesi',    lastPing: _minsAgo(15)  },
  { id: 'KSK-011', pharmacyId: 6, pharmacyName: 'Umut Eczanesi',    lastPing: _minsAgo(4)   },
  { id: 'KSK-012', pharmacyId: 7, pharmacyName: 'Şifa Eczanesi',    lastPing: _minsAgo(6)   },
  { id: 'KSK-013', pharmacyId: 7, pharmacyName: 'Şifa Eczanesi',    lastPing: _minsAgo(360) },
  { id: 'KSK-014', pharmacyId: 8, pharmacyName: 'Nur Eczanesi',     lastPing: _minsAgo(9)   },
];

let _nextId = 9;

function _delay(ms = 350) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Eczane Servisleri ────────────────────────────────────────────────────────

/**
 * Tüm eczaneleri getirir.
 * Gerçek API: return http.get('/api/pharmacies/').then(r => r.data);
 */
export async function getPharmacies() {
  await _delay();
  return _pharmacies.map((p) => ({ ...p }));
}

/**
 * Yeni eczane oluşturur.
 * Gerçek API: return http.post('/api/pharmacies/', data).then(r => r.data);
 * @param {{ name: string, province: string, district: string, owner: string }} data
 */
export async function createPharmacy(data) {
  await _delay();
  const pharmacy = { id: _nextId++, kioskCount: 0, ...data };
  _pharmacies.push(pharmacy);
  return { ...pharmacy };
}

/**
 * Mevcut eczaneyi günceller.
 * Gerçek API: return http.patch(`/api/pharmacies/${id}/`, data).then(r => r.data);
 * @param {number} id
 * @param {{ name?: string, province?: string, district?: string, owner?: string }} data
 */
export async function updatePharmacy(id, data) {
  await _delay();
  const idx = _pharmacies.findIndex((p) => p.id === id);
  if (idx === -1) throw new Error(`Eczane bulunamadı: ${id}`);
  Object.assign(_pharmacies[idx], data);
  return { ..._pharmacies[idx] };
}

/**
 * Eczaneyi siler.
 * Gerçek API: return http.delete(`/api/pharmacies/${id}/`);
 * @param {number} id
 */
export async function deletePharmacy(id) {
  await _delay();
  const idx = _pharmacies.findIndex((p) => p.id === id);
  if (idx !== -1) _pharmacies.splice(idx, 1);
}

// ─── Kiosk Servisleri ─────────────────────────────────────────────────────────

/**
 * Tüm kiosklarının anlık durum bilgisini getirir.
 * Son ping zamanından "Online/Offline" durumu hesaplanır (>10 dk → Offline).
 * Gerçek API: return http.get('/api/pharmacies/kiosk-status/').then(r => r.data);
 */
export async function getKioskStatus() {
  await _delay();
  return _kiosks.map((k) => ({ ...k }));
}
