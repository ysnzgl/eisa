/**
 * Eczane + kiosk verilerini tüm bileşenler arasında paylaşan modül-seviye önbellek.
 * İlk bileşen yüklediğinde tek API çağrısı yapar; sonraki bileşenler önbellekten okur.
 */
import { ref, readonly } from 'vue';
import { getPharmacies, getKioskStatus } from '../services/devices';

const _pharmacies   = ref([]);
const _kiosks       = ref([]);
const _loading      = ref(false);
let   _loaded       = false;
let   _loadPromise  = null;

export function usePharmacyLookups() {
  async function ensureLoaded() {
    if (_loaded) return;
    if (_loadPromise) return _loadPromise;
    _loading.value = true;
    _loadPromise = Promise.all([getPharmacies(), getKioskStatus()])
      .then(([p, k]) => {
        _pharmacies.value = p;
        _kiosks.value     = k;
        _loaded           = true;
      })
      .finally(() => {
        _loading.value = false;
        _loadPromise   = null;
      });
    return _loadPromise;
  }

  return {
    pharmacies: readonly(_pharmacies),
    kiosks:     readonly(_kiosks),
    loading:    readonly(_loading),
    ensureLoaded,
  };
}
