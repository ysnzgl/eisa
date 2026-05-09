<script setup>
/**
 * Pricing Matrix Configurator — DOOH fiyat carpan matrisinin yonetimi.
 * Total = base * duration * frequency_multiplier * (prime_time if prime hour else 1)
 */
import { onMounted, reactive, ref, computed } from 'vue';
import { getPricingMatrix, updatePricingMatrix } from '../../services/dooh';

const loading = ref(false);
const saving = ref(false);
const error = ref('');
const success = ref('');

const form = reactive({
  base_price_per_second: '1.0000',
  prime_time_coefficient: '1.500',
  prime_hours: [17, 18, 19, 20],
  frequency_multipliers: { PER_LOOP: 3.0, PER_HOUR: 1.5, PER_DAY: 1.0 },
  is_default: true,
});

const HOURS = Array.from({ length: 24 }, (_, i) => i);

// Onizleme: ornek bir reklam icin maliyeti hesapla
const preview = reactive({
  duration: 15,
  frequency_type: 'PER_LOOP',
  hour: 18,
});

const previewTotal = computed(() => {
  const base = Number(form.base_price_per_second) || 0;
  const fm = Number(form.frequency_multipliers?.[preview.frequency_type] ?? 1);
  const pt = form.prime_hours.includes(Number(preview.hour))
    ? Number(form.prime_time_coefficient) || 1
    : 1;
  return (base * preview.duration * fm * pt).toFixed(4);
});

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await getPricingMatrix();
    if (data && Object.keys(data).length) {
      form.base_price_per_second = String(data.base_price_per_second ?? '1.0');
      form.prime_time_coefficient = String(data.prime_time_coefficient ?? '1.5');
      form.prime_hours = Array.isArray(data.prime_hours) ? [...data.prime_hours] : [];
      form.frequency_multipliers = { ...(data.frequency_multipliers || {}) };
      form.is_default = data.is_default !== false;
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Pricing matrix yuklenemedi';
  } finally {
    loading.value = false;
  }
}

function toggleHour(h) {
  const i = form.prime_hours.indexOf(h);
  if (i >= 0) form.prime_hours.splice(i, 1);
  else { form.prime_hours.push(h); form.prime_hours.sort((a, b) => a - b); }
}

function setMultiplier(key, value) {
  form.frequency_multipliers[key] = Number(value) || 0;
}

async function save() {
  saving.value = true; error.value = ''; success.value = '';
  try {
    await updatePricingMatrix({
      base_price_per_second: form.base_price_per_second,
      prime_time_coefficient: form.prime_time_coefficient,
      prime_hours: form.prime_hours,
      frequency_multipliers: form.frequency_multipliers,
      is_default: form.is_default,
    });
    success.value = 'Pricing matrix kaydedildi.';
    setTimeout(() => (success.value = ''), 3000);
  } catch (e) {
    error.value = e?.response?.data
      ? JSON.stringify(e.response.data)
      : 'Kaydedilemedi';
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="pricing">
    <header class="page-head">
      <h1>Pricing Matrix Konfigurasyonu</h1>
      <p class="muted">
        DOOH reklam ucretlendirme carpanlarini yonetin.
        <code>total = base &times; duration &times; frequency &times; prime_time</code>
      </p>
    </header>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>
    <div v-if="loading" class="muted">Yukleniyor...</div>

    <div v-else class="grid">
      <div class="card">
        <h2>Temel Fiyatlar</h2>
        <label class="field">
          Saniye basina taban fiyat (TRY)
          <input type="number" step="0.0001" min="0" v-model="form.base_price_per_second" />
        </label>
        <label class="field">
          Prime time carpani
          <input type="number" step="0.001" min="0" v-model="form.prime_time_coefficient" />
        </label>
        <label class="field inline">
          <input type="checkbox" v-model="form.is_default" />
          Varsayilan matrix olarak isaretle
        </label>
      </div>

      <div class="card">
        <h2>Prime Time Saatleri</h2>
        <p class="muted">Prime time'a giren saatleri secin (her biri carpanla carpilir).</p>
        <div class="hour-grid">
          <button
            v-for="h in HOURS"
            :key="h"
            type="button"
            class="hour-cell"
            :class="{ active: form.prime_hours.includes(h) }"
            @click="toggleHour(h)"
          >
            {{ h.toString().padStart(2, '0') }}
          </button>
        </div>
      </div>

      <div class="card">
        <h2>Frekans Carpanlari</h2>
        <p class="muted">Reklam tipine gore fiyat carpani.</p>
        <label class="field" v-for="key in ['PER_LOOP', 'PER_HOUR', 'PER_DAY']" :key="key">
          {{ key }}
          <input
            type="number"
            step="0.01"
            min="0"
            :value="form.frequency_multipliers[key] ?? 1"
            @input="(e) => setMultiplier(key, e.target.value)"
          />
        </label>
      </div>

      <div class="card preview">
        <h2>Onizleme</h2>
        <p class="muted">Ornek reklam icin tahmini maliyet.</p>
        <label class="field">
          Sure (s) <input type="number" min="1" max="60" v-model.number="preview.duration" />
        </label>
        <label class="field">
          Frekans tipi
          <select v-model="preview.frequency_type">
            <option>PER_LOOP</option>
            <option>PER_HOUR</option>
            <option>PER_DAY</option>
          </select>
        </label>
        <label class="field">
          Saat
          <select v-model.number="preview.hour">
            <option v-for="h in HOURS" :key="h" :value="h">{{ h }}:00</option>
          </select>
        </label>
        <div class="total">
          Tahmini fiyat: <strong>{{ previewTotal }} TRY</strong>
          <span v-if="form.prime_hours.includes(Number(preview.hour))" class="badge">PRIME</span>
        </div>
      </div>
    </div>

    <footer class="actions">
      <button class="btn primary" :disabled="saving || loading" @click="save">
        {{ saving ? 'Kaydediliyor...' : 'Kaydet' }}
      </button>
    </footer>
  </section>
</template>

<style scoped>
.pricing { padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; }
.page-head h1 { margin: 0 0 .25rem; font-size: 1.4rem; }
.muted { color: #6b7280; }
.alert-error { background: #fee2e2; color: #991b1b; padding: .75rem 1rem; border-radius: 8px; }
.alert-success { background: #dcfce7; color: #14532d; padding: .75rem 1rem; border-radius: 8px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
.card { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; display: flex; flex-direction: column; gap: .6rem; }
.card h2 { margin: 0; font-size: 1.05rem; color: #1e293b; }
.field { display: flex; flex-direction: column; gap: .25rem; font-size: .85rem; color: #475569; }
.field.inline { flex-direction: row; align-items: center; gap: .5rem; }
.field input, .field select { padding: .45rem .6rem; border: 1px solid #cbd5e1; border-radius: 6px; }
.hour-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: .25rem; }
.hour-cell { background: #f1f5f9; border: 1px solid transparent; border-radius: 6px; padding: .35rem; cursor: pointer; font-size: .8rem; }
.hour-cell.active { background: #2563eb; color: white; }
.preview .total { margin-top: .5rem; font-size: 1.1rem; }
.badge { background: #fbbf24; color: #78350f; padding: .15rem .5rem; border-radius: 999px; font-size: .7rem; margin-left: .5rem; }
.actions { display: flex; justify-content: flex-end; }
.btn.primary { padding: .55rem 1.4rem; background: #2563eb; color: white; border: 0; border-radius: 6px; cursor: pointer; }
.btn.primary:disabled { opacity: .6; cursor: not-allowed; }
</style>
