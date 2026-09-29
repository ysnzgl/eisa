/**
 * i18n altyapısı testleri.
 *
 * Kapsam:
 *   1. Varsayılan dil tr; $t Türkçe döner
 *   2. setLanguage('en') → $t İngilizce döner
 *   3. Bilinmeyen anahtar → anahtarın kendisi döner
 *   4. Değişken interpolasyonu ({name}) çalışır
 *   5. $localize en seçiliyken _en doluysa onu, boşsa Türkçe'ye döner
 *   6. $localize tr seçiliyken her zaman Türkçe base alanı döner
 *   7. toggleLanguage tr↔en değiştirir
 *   8. localStorage'a seçilen dil yazılır
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { language, t, localize, setLanguage, toggleLanguage } from './i18n.js';

beforeEach(() => {
  try { localStorage.clear(); } catch { /* ignore */ }
  setLanguage('tr');
});

describe('i18n $t (sabit metin)', () => {
  it('varsayılan dil tr; Türkçe metin döner', () => {
    setLanguage('tr');
    expect(get(t)('common.continue')).toBe('Devam Et');
    expect(get(t)('common.yes')).toBe('EVET');
  });

  it("setLanguage('en') → İngilizce metin döner", () => {
    setLanguage('en');
    expect(get(t)('common.continue')).toBe('Continue');
    expect(get(t)('common.yes')).toBe('YES');
  });

  it('bilinmeyen anahtar → anahtarın kendisini döner', () => {
    expect(get(t)('does.not.exist')).toBe('does.not.exist');
  });

  it('değişken interpolasyonu {name} çalışır', () => {
    setLanguage('tr');
    expect(get(t)('category.subTitle', { name: 'Uyku' })).toBe('Uyku — alt başlık seçin');
    setLanguage('en');
    expect(get(t)('category.subTitle', { name: 'Sleep' })).toBe('Sleep — select a subcategory');
  });

  it('toggleLanguage tr↔en değiştirir', () => {
    setLanguage('tr');
    toggleLanguage();
    expect(get(language)).toBe('en');
    toggleLanguage();
    expect(get(language)).toBe('tr');
  });

  it('seçilen dil localStorage kiosk_lang anahtarına yazılır', () => {
    setLanguage('en');
    expect(localStorage.getItem('kiosk_lang')).toBe('en');
  });
});

describe('i18n $localize (DB içeriği)', () => {
  const cat = { ad: 'Uyku', ad_en: 'Sleep' };
  const catNoEn = { ad: 'Uyku', ad_en: '' };
  const soru = { metin: 'Yorgun musunuz?', metin_en: 'Are you tired?' };

  it('en seçili + _en dolu → İngilizce alanı döner', () => {
    setLanguage('en');
    expect(get(localize)(cat)).toBe('Sleep');
    expect(get(localize)(soru, 'metin')).toBe('Are you tired?');
  });

  it('en seçili + _en boş → Türkçe base alanına döner', () => {
    setLanguage('en');
    expect(get(localize)(catNoEn)).toBe('Uyku');
  });

  it('tr seçili → her zaman Türkçe base alanı döner', () => {
    setLanguage('tr');
    expect(get(localize)(cat)).toBe('Uyku');
    expect(get(localize)(soru, 'metin')).toBe('Yorgun musunuz?');
  });

  it('null/undefined obje → boş string', () => {
    setLanguage('en');
    expect(get(localize)(null)).toBe('');
    expect(get(localize)(undefined, 'metin')).toBe('');
  });
});
