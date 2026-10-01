<script setup>
/**
 * Sözleşme formu — eczane kaydı ve abonelik yönetiminde ortak kullanılır.
 * `form` reaktif nesnesi parent'a aittir; alanlar doğrudan üzerinde düzenlenir.
 * Demo (gün bazlı, ≤30) veya Standart (12/24/36 ay + öteleme) türünü destekler.
 */
import { computed } from 'vue';

const props = defineProps({
  form: { type: Object, required: true },
  showDurum: { type: Boolean, default: false },
});

const TIPLER = [
  { value: 12, label: '12 Ay' },
  { value: 24, label: '24 Ay' },
  { value: 36, label: '36 Ay' },
];
const DURUMLAR = [
  { value: 'AKTIF', label: 'Aktif' },
  { value: 'IPTAL', label: 'İptal' },
];

const isDemo = computed(() => props.form.tur === 'DEMO');

const toplamAy = computed(() =>
  (Number(props.form.sozlesme_tipi_ay) || 0) + (Number(props.form.oteleme_ay) || 0));
</script>

<template>
  <div class="eisa-form-grid">
    <label class="eisa-form-row">
      <span class="eisa-field-label">Sözleşme Türü</span>
      <select v-model="form.tur" class="eisa-field">
        <option value="STANDART">Standart</option>
        <option value="DEMO">Demo</option>
      </select>
    </label>

    <label v-if="isDemo" class="eisa-form-row">
      <span class="eisa-field-label">Demo Süresi (gün, en fazla 30)</span>
      <input type="number" min="1" max="30" v-model.number="form.demo_gun" class="eisa-field" />
    </label>
    <label v-else class="eisa-form-row">
      <span class="eisa-field-label">Sözleşme Tipi</span>
      <select v-model.number="form.sozlesme_tipi_ay" class="eisa-field">
        <option v-for="t in TIPLER" :key="t.value" :value="t.value">{{ t.label }}</option>
      </select>
    </label>

    <label class="eisa-form-row">
      <span class="eisa-field-label">Başlangıç Tarihi</span>
      <input type="date" v-model="form.baslangic_tarihi" class="eisa-field" />
    </label>

    <label v-if="!isDemo" class="eisa-form-row">
      <span class="eisa-field-label">Kullanım Bedeli Öteleme (ay)</span>
      <input type="number" min="0" max="36" v-model.number="form.oteleme_ay" class="eisa-field" />
    </label>
    <label v-if="!isDemo" class="eisa-form-row">
      <span class="eisa-field-label">Aylık Kullanım Bedeli (TL)</span>
      <input type="number" step="0.01" min="0" v-model="form.aylik_kullanim_bedeli" class="eisa-field" />
    </label>

    <label class="eisa-form-row">
      <span class="eisa-field-label">Cihaz Durumu</span>
      <select v-model="form.cihaz_durumu" class="eisa-field">
        <option value="SATILIK">Satılık</option>
        <option value="KIRALIK">Kiralık</option>
      </select>
    </label>

    <template v-if="form.cihaz_durumu === 'SATILIK'">
      <label class="eisa-form-row">
        <span class="eisa-field-label">Peşin Fiyat (TL)</span>
        <input type="number" step="0.01" min="0" v-model="form.pesin_fiyat" class="eisa-field" />
      </label>
      <label class="eisa-form-row">
        <span class="eisa-field-label">Vade Farkı Oranı (%)</span>
        <input type="number" step="0.01" min="0" v-model="form.vade_farki_orani" class="eisa-field" />
      </label>
      <label class="eisa-form-row">
        <span class="eisa-field-label">Taksit Sayısı</span>
        <select v-model.number="form.taksit_sayisi" class="eisa-field">
          <option :value="1">1 Taksit</option>
          <option :value="4">4 Taksit</option>
          <option :value="8">8 Taksit</option>
          <option :value="12">12 Taksit</option>
        </select>
      </label>
      <label class="eisa-form-row">
        <span class="eisa-field-label">İlk Ödeme Tarihi</span>
        <input type="date" v-model="form.cihaz_baslangic_tarihi" class="eisa-field" />
      </label>
    </template>

    <template v-else>
      <label class="eisa-form-row eisa-form-row-full">
        <span class="eisa-field-label">Aylık Cihaz Kira Bedeli (TL)</span>
        <input type="number" step="0.01" min="0" v-model="form.cihaz_kira_bedeli" class="eisa-field" />
      </label>
    </template>

    <label v-if="showDurum" class="eisa-form-row">
      <span class="eisa-field-label">Durum</span>
      <select v-model="form.durum" class="eisa-field">
        <option v-for="d in DURUMLAR" :key="d.value" :value="d.value">{{ d.label }}</option>
      </select>
    </label>

    <label class="eisa-form-row eisa-form-row-full">
      <span class="eisa-field-label">Notlar</span>
      <textarea v-model="form.notlar" rows="2" class="eisa-field"></textarea>
    </label>

    <p v-if="isDemo" class="eisa-reset-info eisa-form-row-full">
      <i class="fa-solid fa-circle-info"></i>
      Demo sözleşmede kullanım bedeli faturalanmaz ve hesap kısıtlanmaz. Süre en fazla 30 gündür.
    </p>
    <p v-else class="eisa-reset-info eisa-form-row-full">
      <i class="fa-solid fa-circle-info"></i>
      Toplam süre: <strong>{{ toplamAy }} ay</strong> (vade kaydırma dahil). İlk
      {{ form.oteleme_ay || 0 }} ay kullanım bedeli faturası kesilmez.
    </p>
  </div>
</template>
