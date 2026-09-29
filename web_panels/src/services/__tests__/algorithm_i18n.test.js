/**
 * algorithm.js TR/EN ceviri alani eslemesi testleri.
 *
 * Kapsam:
 *   1. mapCategoryFromApi ad_en → name_en
 *   2. createCategory/updateCategory name_en → ad_en payload
 *   3. mapQuestionFromApi metin_en → text_en
 *   4. createQuestion/updateQuestion text_en → metin_en payload
 *   5. mapDanismaFromApi ad_en korunur
 *   6. createDanisma/updateDanisma ad_en payload
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('axios', async () => {
  const mockHttp = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  return {
    default: { create: vi.fn(() => mockHttp) },
    __mockHttp: mockHttp,
  };
});

import {
  getCategories,
  createCategory,
  updateCategory,
  getQuestions,
  createQuestion,
  updateQuestion,
  getDanismaKategorileri,
  createDanisma,
  updateDanisma,
} from '../../services/algorithm.js';

describe('algorithm.js TR/EN eslemesi', () => {
  let http;

  beforeEach(async () => {
    vi.clearAllMocks();
    const { default: axiosMock } = await import('axios');
    http = axiosMock.create();
  });

  it('mapCategoryFromApi ad_en → name_en', async () => {
    http.get.mockResolvedValue({ data: [{ id: 1, ad: 'Uyku', ad_en: 'Sleep', slug: 'uyku' }] });
    const cats = await getCategories();
    expect(cats[0].name).toBe('Uyku');
    expect(cats[0].name_en).toBe('Sleep');
  });

  it('createCategory name_en → ad_en payload', async () => {
    http.post.mockResolvedValue({ data: { id: 2, ad: 'Enerji', ad_en: 'Energy', slug: 'enerji' } });
    await createCategory({ name: 'Enerji', name_en: 'Energy', slug: 'enerji' });
    const payload = http.post.mock.calls[0][1];
    expect(payload.ad).toBe('Enerji');
    expect(payload.ad_en).toBe('Energy');
  });

  it('updateCategory name_en → ad_en payload', async () => {
    http.patch.mockResolvedValue({ data: { id: 2, ad: 'Enerji', ad_en: 'Vitality', slug: 'enerji' } });
    await updateCategory(2, { name_en: 'Vitality' });
    const payload = http.patch.mock.calls[0][1];
    expect(payload.ad_en).toBe('Vitality');
  });

  it('mapQuestionFromApi metin_en → text_en', async () => {
    http.get.mockResolvedValue({
      data: [{ id: 5, kategori: 1, metin: 'Yorgun musunuz?', metin_en: 'Are you tired?', sira: 1 }],
    });
    const qs = await getQuestions(1);
    expect(qs[0].text).toBe('Yorgun musunuz?');
    expect(qs[0].text_en).toBe('Are you tired?');
  });

  it('createQuestion text_en → metin_en payload', async () => {
    http.post.mockResolvedValue({ data: { id: 6, kategori: 1, metin: 'Q', metin_en: 'Q-en', sira: 0 } });
    await createQuestion(1, { text: 'Q', text_en: 'Q-en' });
    const payload = http.post.mock.calls[0][1];
    expect(payload.metin).toBe('Q');
    expect(payload.metin_en).toBe('Q-en');
  });

  it('updateQuestion text_en → metin_en payload', async () => {
    http.patch.mockResolvedValue({ data: { id: 6, kategori: 1, metin: 'Q', metin_en: 'Q-en2', sira: 0 } });
    await updateQuestion(6, { text_en: 'Q-en2' });
    const payload = http.patch.mock.calls[0][1];
    expect(payload.metin_en).toBe('Q-en2');
  });

  it('mapDanismaFromApi ad_en korunur', async () => {
    http.get.mockResolvedValue({ data: [{ id: 9, ad: 'Kadin', ad_en: "Women's Health", slug: 'kadin' }] });
    const list = await getDanismaKategorileri();
    expect(list[0].ad).toBe('Kadin');
    expect(list[0].ad_en).toBe("Women's Health");
  });

  it('createDanisma ad_en payload', async () => {
    http.post.mockResolvedValue({ data: { id: 9, ad: 'Kadin', ad_en: 'Women', slug: 'kadin' } });
    await createDanisma({ ad: 'Kadin', ad_en: 'Women', slug: 'kadin' });
    const payload = http.post.mock.calls[0][1];
    expect(payload.ad_en).toBe('Women');
  });

  it('updateDanisma ad_en payload', async () => {
    http.patch.mockResolvedValue({ data: { id: 9, ad: 'Kadin', ad_en: 'Women Health', slug: 'kadin' } });
    await updateDanisma(9, { ad_en: 'Women Health' });
    const payload = http.patch.mock.calls[0][1];
    expect(payload.ad_en).toBe('Women Health');
  });
});
