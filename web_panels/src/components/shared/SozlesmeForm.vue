<script setup>
import { computed, watch } from 'vue';

const props = defineProps({
  form: { type: Object, required: true },
});

const KDV_SECENEKLER = [
  { value: 0, label: '%0 (KDV Yok)' },
  { value: 1, label: '%1' },
  { value: 10, label: '%10' },
  { value: 20, label: '%20' },
];
const TEVKIFAT_SECENEKLER = [
  { value: '', label: 'Yok' },
  ...['1','2','3','4','5','6','7','8','9'].map(n => ({ value: `${n}/10`, label: `${n}/10` })),
];

const isDemo = computed(() => props.form.tur === 'DEMO');
const toplamAy = computed(() =>
  (Number(props.form.sozlesme_tipi_ay) || 0) + (Number(props.form.oteleme_ay) || 0));

const abKdv = computed(() => (Number(props.form.aylik_kullanim_bedeli) || 0) * (Number(props.form.kdv_orani) || 0) / 100);
const abKdvDahil = computed(() => (Number(props.form.aylik_kullanim_bedeli) || 0) + abKdv.value);
const abTevkifatKesri = computed(() => {
  if (!props.form.tevkifat_orani) return 0;
  const [p, d] = props.form.tevkifat_orani.split('/');
  return Number(p) / Number(d);
});
const abTevkifat = computed(() => abKdv.value * abTevkifatKesri.value);
const abNet = computed(() => abKdvDahil.value - abTevkifat.value);
const hasAbKdv = computed(() => !isDemo.value && Number(props.form.kdv_orani) > 0);

function planToplamSatilik(p) {
  return (Number(p.adet) || 1) * (Number(p.pesin_fiyat) || 0) * (1 + (Number(p.vade_farki_orani) || 0) / 100);
}
function planToplamKiralik(p) {
  return (Number(p.aylik_kira_bedeli) || 0) * (Number(p.adet) || 1);
}
function planToplam(p) { return p.tip === 'KIRALIK' ? planToplamKiralik(p) : planToplamSatilik(p); }
function planKdvTutari(p) { return planToplam(p) * (Number(p.cihaz_kdv_orani) || 0) / 100; }
function planKdvDahil(p) { return planToplam(p) + planKdvTutari(p); }
function planTevkifatKesri(p) {
  if (!p.tevkifat_orani) return 0;
  const [a, b] = p.tevkifat_orani.split('/');
  return Number(a) / Number(b);
}
function planTevkifat(p) { return planKdvTutari(p) * planTevkifatKesri(p); }
function planNet(p) { return planKdvDahil(p) - planTevkifat(p); }
function planTaksit(p) {
  if (p.tip === 'KIRALIK') return planKdvDahil(p);
  const n = Math.max(1, Number(p.taksit_sayisi) || 1);
  return planKdvDahil(p) / n;
}

const planlar = computed(() => props.form.cihaz_planlari || []);
const toplamSatilikKdvDahil = computed(() => planlar.value.filter(p => p.tip !== 'KIRALIK').reduce((s, p) => s + planKdvDahil(p), 0));
const toplamKiralikAylik = computed(() => planlar.value.filter(p => p.tip === 'KIRALIK').reduce((s, p) => s + planKdvDahil(p), 0));

const emptyPlan = () => ({
  tip: 'SATILIK', adet: 1, cihaz_bilgisi: '',
  pesin_fiyat: '', vade_farki_orani: '0.00', taksit_sayisi: 1,
  aylik_kira_bedeli: '',
  cihaz_kdv_orani: 0, tevkifat_orani: '',
  oteleme_ay: 0,
  baslangic_tarihi: props.form.baslangic_tarihi || '',
});

function addPlan() {
  if (!props.form.cihaz_planlari) props.form.cihaz_planlari = [];
  props.form.cihaz_planlari.push(emptyPlan());
}
function removePlan(idx) { props.form.cihaz_planlari.splice(idx, 1); }

// Sözleşme başlangıcı değişince tüm cihaz planların fatura tarihi de aynı tarihe senkronlanır.
watch(() => props.form.baslangic_tarihi, (val) => {
  if (!val) return;
  props.form.cihaz_baslangic_tarihi = val;
  (props.form.cihaz_planlari || []).forEach(p => { p.baslangic_tarihi = val; });
}, { immediate: true });

function fmtTL(v) {
  return Number(v || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '\u202f\u20ba';
}
</script>
<template>
  <div class="sf-wrapper">
    <!-- ━━ BÖLÜM 1: SÖZLEŞME ━━ -->
    <div class="sf-section">
      <div class="sf-section-header"><i class="fa-solid fa-file-contract"></i> Sözleşme Bilgileri</div>
      <div class="eisa-form-grid sf-section-body">
        <label class="eisa-form-row"><span class="eisa-field-label">Tür</span>
          <select v-model="form.tur" class="eisa-field"><option value="STANDART">Standart</option><option value="DEMO">Demo</option></select>
        </label>
        <label v-if="isDemo" class="eisa-form-row"><span class="eisa-field-label">Demo Süresi (gün, ≤30)</span>
          <input type="number" min="1" max="30" v-model.number="form.demo_gun" class="eisa-field" />
        </label>
        <label v-else class="eisa-form-row"><span class="eisa-field-label">Süre</span>
          <select v-model.number="form.sozlesme_tipi_ay" class="eisa-field">
            <option :value="12">12 Ay</option><option :value="24">24 Ay</option><option :value="36">36 Ay</option>
          </select>
        </label>
        <label class="eisa-form-row"><span class="eisa-field-label">Başlangıç Tarihi</span>
          <input type="date" v-model="form.baslangic_tarihi" class="eisa-field" />
        </label>
        <label v-if="!isDemo" class="eisa-form-row"><span class="eisa-field-label">Kullanım Bedeli Öteleme (ay)</span>
          <input type="number" min="0" max="36" v-model.number="form.oteleme_ay" class="eisa-field" />
        </label>
        <label class="eisa-form-row eisa-form-row-full"><span class="eisa-field-label">Notlar</span>
          <textarea v-model="form.notlar" rows="2" class="eisa-field"></textarea>
        </label>
        <p v-if="!isDemo" class="eisa-reset-info eisa-form-row-full">
          <i class="fa-solid fa-circle-info"></i> Toplam süre: <strong>{{ toplamAy }} ay</strong> (öteleme dahil).
        </p>
      </div>
    </div>
    <!-- ━━ BÖLÜM 2: ABONELK & ÖDEME ━━ -->
    <div v-if="!isDemo" class="sf-section">
      <div class="sf-section-header"><i class="fa-solid fa-receipt"></i> Abonelik &amp; Ödeme</div>
      <div class="eisa-form-grid sf-section-body">
        <label class="eisa-form-row"><span class="eisa-field-label">Aylık Kullanım Bedeli</span>
          <div class="eisa-input-group"><input type="number" step="0.01" min="0" v-model="form.aylik_kullanim_bedeli" class="eisa-field" /><span class="eisa-input-suffix">₺</span></div>
        </label>
        <label class="eisa-form-row"><span class="eisa-field-label">KDV Oranı</span>
          <select v-model.number="form.kdv_orani" class="eisa-field">
            <option v-for="k in KDV_SECENEKLER" :key="k.value" :value="k.value">{{ k.label }}</option>
          </select>
        </label>
        <label v-if="form.kdv_orani > 0" class="eisa-form-row"><span class="eisa-field-label">Tevkifat Oranı</span>
          <select v-model="form.tevkifat_orani" class="eisa-field">
            <option v-for="t in TEVKIFAT_SECENEKLER" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </label>
        <label class="eisa-form-row"><span class="eisa-field-label">Erken İptal Ceza Katsayısı</span>
          <div class="eisa-input-group"><input type="number" step="0.1" min="0" v-model="form.iptal_ceza_orani" class="eisa-field" placeholder="2" /><span class="eisa-input-suffix">× aylık</span></div>
        </label>
        <div class="sf-tutar-grid eisa-form-row-full">
          <div class="sf-tutar-kalem"><span>Matrah</span><strong>{{ fmtTL(form.aylik_kullanim_bedeli) }}</strong></div>
          <template v-if="hasAbKdv">
            <div class="sf-tutar-sep">+</div>
            <div class="sf-tutar-kalem"><span>KDV (%{{ form.kdv_orani }})</span><strong>{{ fmtTL(abKdv) }}</strong></div>
            <div class="sf-tutar-sep">=</div>
            <div class="sf-tutar-kalem sf-tutar-accent"><span>KDV Dahil</span><strong>{{ fmtTL(abKdvDahil) }}</strong></div>
          </template>
          <template v-if="form.tevkifat_orani">
            <div class="sf-tutar-sep">−</div>
            <div class="sf-tutar-kalem"><span>Tevkifat ({{ form.tevkifat_orani }})</span><strong>{{ fmtTL(abTevkifat) }}</strong></div>
            <div class="sf-tutar-sep">=</div>
            <div class="sf-tutar-kalem sf-tutar-accent"><span>Net Ödeme</span><strong>{{ fmtTL(abNet) }}</strong></div>
          </template>
        </div>
      </div>
    </div>
    <!-- ━━ BÖLÜM 3: CİHAZLAR ━━ -->
    <div class="sf-section">
      <div class="sf-section-header">
        <i class="fa-solid fa-display"></i> Cihazlar
        <span class="sf-section-badge">{{ (form.cihaz_planlari || []).length }} plan</span>
      </div>
      <div class="sf-section-body">
        <p class="eisa-reset-info" style="margin:0 0 .6rem;">
          <i class="fa-solid fa-circle-info"></i>
          Tüm cihaz bedelleri, abonelik ile aynı tarihte tek birleşik faturada tahsil edilir.
        </p>
        <div v-for="(p, i) in form.cihaz_planlari" :key="i" class="sf-plan-card">
          <div class="sf-plan-card-header">
            <span>
              <i class="fa-solid fa-display"></i> Cihaz {{ i + 1 }}
              <span class="eisa-pill" :class="p.tip === 'KIRALIK' ? 'eisa-pill-warning' : 'eisa-pill-info'" style="margin-left:.4rem;font-size:.72rem;">{{ p.tip === 'KIRALIK' ? 'Kiralık' : 'Satılık' }}</span>
            </span>
            <button type="button" class="sf-plan-remove" @click="removePlan(i)"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="eisa-form-grid" style="margin:0;">
            <label class="eisa-form-row"><span class="eisa-field-label">Tip</span>
              <select v-model="p.tip" class="eisa-field"><option value="SATILIK">Satılık</option><option value="KIRALIK">Kiralık</option></select>
            </label>
            <label class="eisa-form-row"><span class="eisa-field-label">Adet</span>
              <input type="number" min="1" max="99" v-model.number="p.adet" class="eisa-field" />
            </label>
            <label class="eisa-form-row eisa-form-row-full"><span class="eisa-field-label">Cihaz Bilgisi</span>
              <input type="text" v-model="p.cihaz_bilgisi" class="eisa-field" placeholder="Marka/model, model no, notlar" />
            </label>
            <template v-if="p.tip === 'SATILIK'">
              <label class="eisa-form-row"><span class="eisa-field-label">Birim Peşin Fiyat</span>
                <div class="eisa-input-group sf-pesin-group"><input type="number" step="0.01" min="0" v-model="p.pesin_fiyat" class="eisa-field" /><span class="eisa-input-suffix">₺</span></div>
              </label>
              <label class="eisa-form-row"><span class="eisa-field-label">Vade Farkı</span>
                <div class="eisa-input-group"><input type="number" step="0.01" min="0" v-model="p.vade_farki_orani" class="eisa-field" :disabled="Number(p.taksit_sayisi) <= 1" /><span class="eisa-input-suffix">%</span></div>
              </label>
              <label class="eisa-form-row"><span class="eisa-field-label">Taksit Sayısı (1–12)</span>
                <input type="number" min="1" max="12" v-model.number="p.taksit_sayisi" class="eisa-field" />
              </label>
            </template>
            <label v-else class="eisa-form-row"><span class="eisa-field-label">Birim Aylık Kira</span>
              <div class="eisa-input-group"><input type="number" step="0.01" min="0" v-model="p.aylik_kira_bedeli" class="eisa-field" /><span class="eisa-input-suffix">₺</span></div>
            </label>
            <label class="eisa-form-row"><span class="eisa-field-label">Cihaz Öteleme (ay)</span>
              <input type="number" min="0" max="36" v-model.number="p.oteleme_ay" class="eisa-field" />
            </label>
            <label class="eisa-form-row"><span class="eisa-field-label">KDV Oranı</span>
              <select v-model.number="p.cihaz_kdv_orani" class="eisa-field">
                <option v-for="k in KDV_SECENEKLER" :key="k.value" :value="k.value">{{ k.label }}</option>
              </select>
            </label>
            <label v-if="p.cihaz_kdv_orani > 0" class="eisa-form-row"><span class="eisa-field-label">Tevkifat Oranı</span>
              <select v-model="p.tevkifat_orani" class="eisa-field">
                <option v-for="t in TEVKIFAT_SECENEKLER" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </label>
          </div>
          <div class="sf-tutar-grid" style="margin-top:.5rem;">
            <div class="sf-tutar-kalem">
              <span>{{ p.tip === 'KIRALIK' ? 'Aylık' : 'Toplam' }}</span>
              <strong>{{ fmtTL(planToplam(p)) }}</strong>
            </div>
            <template v-if="Number(p.cihaz_kdv_orani) > 0">
              <div class="sf-tutar-sep">+</div>
              <div class="sf-tutar-kalem"><span>KDV (%{{ p.cihaz_kdv_orani }})</span><strong>{{ fmtTL(planKdvTutari(p)) }}</strong></div>
              <div class="sf-tutar-sep">=</div>
              <div class="sf-tutar-kalem sf-tutar-accent"><span>{{ p.tip === 'KIRALIK' ? 'KDV Dahil' : 'KDV Dahil' }}</span><strong>{{ fmtTL(planKdvDahil(p)) }}</strong></div>
            </template>
            <template v-if="p.tevkifat_orani">
              <div class="sf-tutar-sep">−</div>
              <div class="sf-tutar-kalem"><span>Tevkifat ({{ p.tevkifat_orani }})</span><strong>{{ fmtTL(planTevkifat(p)) }}</strong></div>
              <div class="sf-tutar-sep">=</div>
              <div class="sf-tutar-kalem sf-tutar-accent"><span>Net</span><strong>{{ fmtTL(planNet(p)) }}</strong></div>
            </template>
            <template v-if="p.tip === 'SATILIK' && Number(p.taksit_sayisi) > 1">
              <div class="sf-tutar-sep">÷{{ p.taksit_sayisi }}</div>
              <div class="sf-tutar-kalem sf-tutar-accent"><span>Aylık Taksit</span><strong>{{ fmtTL(planTaksit(p)) }}</strong></div>
            </template>
          </div>
          <p class="eisa-reset-info" style="margin:.4rem 0 0;font-size:.72rem;">
            <i class="fa-solid fa-circle-info"></i>
            {{ Number(p.oteleme_ay) > 0
              ? `İlk cihaz faturası sözleşme başlangıcından ${p.oteleme_ay} ay sonra kesilir.`
              : 'İlk cihaz faturası sözleşme tarihiyle aynı dönemde kesilir.' }}
          </p>
        </div>
        <button type="button" class="sf-add-plan" @click="addPlan">
          <i class="fa-solid fa-plus-circle"></i> Cihaz Ekle
        </button>
      </div>
    </div>
    <!-- ━━ TOPLAM ÖZET ━━ -->
    <div v-if="!isDemo && (planlar.length > 0 || Number(form.aylik_kullanim_bedeli) > 0)" class="sf-section">
      <div class="sf-section-header"><i class="fa-solid fa-calculator"></i> Toplam Özet</div>
      <div class="eisa-form-grid sf-section-body">
        <div class="sf-tutar-kalem">
          <span>Aylık Abonelik (KDV dahil)</span>
          <strong style="font-size:1rem;">{{ fmtTL(hasAbKdv ? abKdvDahil : form.aylik_kullanim_bedeli) }}</strong>
        </div>
        <div v-if="toplamKiralikAylik > 0" class="sf-tutar-kalem">
          <span>Kiralık Cihaz Toplam / Ay</span>
          <strong style="font-size:1rem;">{{ fmtTL(toplamKiralikAylik) }}</strong>
        </div>
        <div v-if="toplamSatilikKdvDahil > 0" class="sf-tutar-kalem">
          <span>Satın Alınan Cihaz Toplam</span>
          <strong style="font-size:1rem;">{{ fmtTL(toplamSatilikKdvDahil) }}</strong>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.sf-wrapper { display:flex; flex-direction:column; gap:.75rem; }
.sf-section { border:1px solid var(--border); border-radius:12px; overflow:hidden; }
.sf-section-header {
  display:flex; align-items:center; gap:.5rem;
  padding:.6rem 1rem; background:#F8FAFC;
  border-bottom:1px solid var(--border);
  font-size:.78rem; font-weight:700; text-transform:uppercase;
  letter-spacing:.05em; color:#4B5563;
}
.sf-section-header i { color:var(--primary); font-size:.85rem; }
.sf-section-badge { margin-left:auto; background:#E0E7FF; color:#3730A3; padding:.1rem .5rem; border-radius:99px; font-size:.72rem; font-weight:600; }
.sf-section-body { padding:.875rem 1rem; }

/* Tutar özet satırı */
.sf-tutar-grid { display:flex; align-items:center; flex-wrap:wrap; gap:.35rem .5rem; padding:.6rem .75rem; background:#F0F9FF; border-radius:8px; }
.sf-tutar-kalem { display:flex; flex-direction:column; align-items:flex-start; }
.sf-tutar-kalem span { font-size:.68rem; color:#6B7280; }
.sf-tutar-kalem strong { font-size:.82rem; color:#1F2937; }
.sf-tutar-sep { color:#9CA3AF; font-size:.95rem; font-weight:600; align-self:flex-end; padding-bottom:.1rem; }
.sf-tutar-accent strong { color:var(--primary); font-weight:700; }

/* Cihaz plan kartı */
.sf-plan-list { display:flex; flex-direction:column; gap:.625rem; }
.sf-plan-card { border:1px solid var(--border); border-radius:10px; padding:.75rem; background:#fff; }
.sf-plan-card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:.6rem; font-size:.8rem; font-weight:700; color:#374151; }
.sf-plan-card-header i { color:var(--primary); margin-right:.3rem; }
.sf-plan-remove { border:none; background:none; cursor:pointer; color:#EF4444; font-size:.9rem; padding:.15rem .4rem; border-radius:4px; }
.sf-plan-remove:hover { background:#FEF2F2; }
.sf-add-plan {
  display:flex; align-items:center; gap:.4rem; justify-content:center;
  border:2px dashed var(--border); border-radius:10px; padding:.625rem;
  background:none; cursor:pointer; color:var(--primary); font-size:.82rem; font-weight:600;
  width:100%; transition:background .15s;
}
.sf-add-plan:hover { background:#EFF6FF; }

.sf-wrapper :deep(.sf-pesin-group) {
  border: 1px solid var(--border-default);
}
</style>
