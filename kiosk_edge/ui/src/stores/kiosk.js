import { writable } from 'svelte/store';

// Ekran state makinesi: idle | demographics | welcome | category | sensitive | question | result
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

// Yükleme durumları
export const catsLoading     = writable(false);
export const questionsLoading = writable(false);

// Sonuç state'i: { label, ana, destek, recs, isSensitive, qrCode }
export const result = writable(null);

// Kampanya state'i
export const campaigns = writable([]);
export const showCampaignOverlay = writable(false);
export const activeCampaignIndex = writable(0);
