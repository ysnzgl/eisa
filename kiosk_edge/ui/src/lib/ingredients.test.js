/**
 * Etken madde öneri motoru testleri.
 *
 * Kapsam:
 *   1. Tek soruda birden fazla etken madde — hepsi sonuçta bulunmalı
 *   2. Birden fazla sorudan gelen farklı maddeler birleştirilmeli
 *   3. Aynı madde farklı sorulardan gelirse tekilleştirilmeli (ilk sıra korunur)
 *   4. recsToIngredientList — tüm tekil maddeleri düz liste olarak döndürmeli
 *   5. Cinsiyete uymayan kural eşleşmemeli
 *   6. Yaş aralığına uymayan kural eşleşmemeli
 *   7. Yanıt 'N' olan sorular göz ardı edilmeli
 *   8. Yanıt 'Y' olmayan / boş cevap durumu
 */
import { describe, it, expect } from 'vitest';
import { getRecommendations, recsToIngredientList, representativeAge } from './ingredients.js';

// ── Yardımcılar ───────────────────────────────────────────────────────────────

/** Verilen maddeler için eşleşme kuralları üreten yardımcı. */
function makeQuestion(seedId, ingredients, { gender = ['M', 'F'], ageMin = 0, ageMax = 200 } = {}) {
  return {
    seed_id: seedId,
    eslesme_kurallari: ingredients.map((ing) => ({
      gender,
      age_min: ageMin,
      age_max: ageMax,
      primary: ing,
      supportive: '',
    })),
  };
}

function makeAnswer(id, answer = 'Y') {
  return { id, answer };
}

// ── 1. Tek soruda birden fazla etken madde ────────────────────────────────────

describe('tek soruda birden fazla etken madde', () => {
  it('soruya bağlı A, B, C maddeleri hepsini döndürür', () => {
    const questions = [makeQuestion('q1', ['A', 'B', 'C'])];
    const answers = [makeAnswer('q1')];
    const recs = getRecommendations(questions, answers, '26-35', 'M');
    const names = recs.map((r) => r.primary);
    expect(names).toEqual(['A', 'B', 'C']);
  });

  it('tek maddeli soru tek madde döndürür', () => {
    const questions = [makeQuestion('q1', ['Magnezyum'])];
    const answers = [makeAnswer('q1')];
    const recs = getRecommendations(questions, answers, '18-25', 'F');
    expect(recs).toHaveLength(1);
    expect(recs[0].primary).toBe('Magnezyum');
  });
});

// ── 2. Birden fazla sorudan farklı maddeler ───────────────────────────────────

describe('birden fazla sorudan farklı maddeler birleştirilir', () => {
  it('örnek: Q1→A,B,C  Q2→B,D  Q3→A,C,E  ⟹  A,B,C,D,E', () => {
    const questions = [
      makeQuestion('q1', ['A', 'B', 'C']),
      makeQuestion('q2', ['B', 'D']),
      makeQuestion('q3', ['A', 'C', 'E']),
    ];
    const answers = [makeAnswer('q1'), makeAnswer('q2'), makeAnswer('q3')];
    const recs = getRecommendations(questions, answers, '36-50', 'M');
    const names = recs.map((r) => r.primary);
    expect(names).toEqual(['A', 'B', 'C', 'D', 'E']);
  });
});

// ── 3. Tekilleştirme: aynı madde farklı sorulardan ───────────────────────────

describe('tekilleştirme', () => {
  it('aynı madde iki sorudan gelirse sonuçta bir kez görünür', () => {
    const questions = [
      makeQuestion('q1', ['Magnezyum', 'B12']),
      makeQuestion('q2', ['B12', 'D3']),
    ];
    const answers = [makeAnswer('q1'), makeAnswer('q2')];
    const recs = getRecommendations(questions, answers, '18-25', 'F');
    const names = recs.map((r) => r.primary);
    expect(names).toEqual(['Magnezyum', 'B12', 'D3']);
  });

  it('ilk görülme sırası korunur', () => {
    const questions = [
      makeQuestion('q1', ['C', 'A']),
      makeQuestion('q2', ['A', 'B']),
    ];
    const answers = [makeAnswer('q1'), makeAnswer('q2')];
    const recs = getRecommendations(questions, answers, '26-35', 'M');
    const names = recs.map((r) => r.primary);
    expect(names[0]).toBe('C');
    expect(names[1]).toBe('A');
    expect(names[2]).toBe('B');
    expect(names).toHaveLength(3);
  });
});

// ── 4. recsToIngredientList ───────────────────────────────────────────────────

describe('recsToIngredientList', () => {
  it('tüm tekil maddeleri düz liste olarak döndürür', () => {
    const questions = [
      makeQuestion('q1', ['A', 'B', 'C']),
      makeQuestion('q2', ['B', 'D']),
      makeQuestion('q3', ['A', 'C', 'E']),
    ];
    const answers = [makeAnswer('q1'), makeAnswer('q2'), makeAnswer('q3')];
    const recs = getRecommendations(questions, answers, '18-25', 'M');
    const list = recsToIngredientList(recs);
    expect(list).toEqual(['A', 'B', 'C', 'D', 'E']);
  });

  it('boş recs için boş liste döner', () => {
    expect(recsToIngredientList([])).toEqual([]);
  });
});

// ── 5. Cinsiyete uymayan kural ────────────────────────────────────────────────

describe('cinsiyet filtresi', () => {
  it('yalnızca M için tanımlanan kural F cinsiyetine eşleşmez', () => {
    const questions = [makeQuestion('q1', ['Demir'], { gender: ['M'] })];
    const answers = [makeAnswer('q1')];
    const recs = getRecommendations(questions, answers, '26-35', 'F');
    expect(recs).toHaveLength(0);
  });

  it('M ve F için tanımlanan kural her ikisine de eşleşir', () => {
    const questions = [makeQuestion('q1', ['B12'], { gender: ['M', 'F'] })];
    expect(getRecommendations(questions, [makeAnswer('q1')], '26-35', 'M')).toHaveLength(1);
    expect(getRecommendations(questions, [makeAnswer('q1')], '26-35', 'F')).toHaveLength(1);
  });
});

// ── 6. Yaş aralığına uymayan kural ───────────────────────────────────────────

describe('yaş aralığı filtresi', () => {
  it('65+ yaş grubunda 0-17 için tanımlı kural eşleşmez', () => {
    const questions = [makeQuestion('q1', ['Kalsiyum'], { ageMin: 0, ageMax: 17 })];
    const answers = [makeAnswer('q1')];
    const recs = getRecommendations(questions, answers, '65+', 'F');
    expect(recs).toHaveLength(0);
  });

  it('yaş tam sınırda eşleşir', () => {
    const questions = [makeQuestion('q1', ['Demir'], { ageMin: 18, ageMax: 25 })];
    const answers = [makeAnswer('q1')];
    // 18-25 aralığının temsili yaşı 21
    expect(representativeAge('18-25')).toBe(21);
    const recs = getRecommendations(questions, answers, '18-25', 'M');
    expect(recs).toHaveLength(1);
  });
});

// ── 7. Yanıt 'N' olan sorular ────────────────────────────────────────────────

describe("yanıt 'N' olan sorular göz ardı edilir", () => {
  it("answer='N' sorusu sonuç üretmez", () => {
    const questions = [makeQuestion('q1', ['A', 'B'])];
    const answers = [makeAnswer('q1', 'N')];
    const recs = getRecommendations(questions, answers, '26-35', 'M');
    expect(recs).toHaveLength(0);
  });

  it('karışık: bazı N bazı Y', () => {
    const questions = [
      makeQuestion('q1', ['A']),
      makeQuestion('q2', ['B']),
    ];
    const answers = [makeAnswer('q1', 'N'), makeAnswer('q2', 'Y')];
    const recs = getRecommendations(questions, answers, '26-35', 'F');
    expect(recs.map((r) => r.primary)).toEqual(['B']);
  });
});

// ── 8. Kenar durumlar ────────────────────────────────────────────────────────

describe('kenar durumlar', () => {
  it('boş sorular → boş sonuç', () => {
    expect(getRecommendations([], [], '26-35', 'M')).toEqual([]);
  });

  it('boş cevaplar → boş sonuç', () => {
    const questions = [makeQuestion('q1', ['A'])];
    expect(getRecommendations(questions, [], '26-35', 'M')).toEqual([]);
  });

  it('yanıt olmayan soru → sonuç yok', () => {
    const questions = [makeQuestion('q1', ['A'])];
    const answers = [makeAnswer('q99', 'Y')]; // q1 ile eşleşmiyor
    const recs = getRecommendations(questions, answers, '26-35', 'M');
    expect(recs).toHaveLength(0);
  });
});
