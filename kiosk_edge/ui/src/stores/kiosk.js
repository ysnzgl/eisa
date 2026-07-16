import { writable } from 'svelte/store';

// Ekran state makinesi:
//   wifi_setup | idle | demographics | welcome | category | consult | question | result
export const screen = writable('idle');

// Demografik seçimler
export const selectedAge = writable(null);
export const selectedSex = writable(null);

// Kategori & soru akışı
export const allCategories   = writable([]);
export const visibleCategories = writable([]);
export const currentCategory = writable(null);
export const currentQuestions = writable([]);
export const currentAnswers  = writable([]);
export const currentQIndex   = writable(0);

// Danışma akışı
export const danismaCategories = writable([]);
export const danismaLoading    = writable(false);
export const selectedDanismaParent = writable(null);

// Yükleme durumları
export const catsLoading     = writable(false);
export const questionsLoading = writable(false);

// Sonuç state'i: { label, ana, destek, recs, isSensitive, qrCode, qrPayload }
export const result = writable(null);

// Kampanya state'i
export const campaigns = writable([]);
export const showCampaignOverlay = writable(false);
export const activeCampaignIndex = writable(0);

// Playlist state'i (DOOH — api-node'dan gelir)
export const playlistItems        = writable([]);   // [ { id, asset_id, asset_type, media_url, duration_seconds, ... } ]
export const playlistVersion      = writable(0);    // son yüklenen versiyon
export const playlistHour         = writable(-1);   // hangi saat için yüklendi
export const playlistIsFallback   = writable(true); // gerçek playlist mi, fallback mı
