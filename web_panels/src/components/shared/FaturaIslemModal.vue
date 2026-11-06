<script setup>
import { computed, onMounted, ref } from 'vue';
import { getFaturaAdmin, previewFaturaRebuild, correctFatura } from '../../services/abonelik';

const props = defineProps({ fatura: { type: Object, required: true }, action: { type: String, required: true } });
const emit = defineEmits(['close', 'saved']);
const current = ref(null);
const preview = ref(null);
const neden = ref('');
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const title = computed(() => ({ iptal: 'Faturayı İptal Et', 'yeniden-olustur': 'Faturayı Yeniden Oluştur',
  'odemeyi-geri-al': 'Tahsilat Kaydını Geri Al' }[props.action]));
const fmt = (v) => Number(v || 0).toLocaleString('tr-TR', { style: 'currency', currency: 'TRY' });

async function load() {
  loading.value = true;
  error.value = '';
  current.value = null;
  preview.value = null;
  try {
    const { data } = await getFaturaAdmin(props.fatura.id);
    current.value = data;
    if (props.action === 'yeniden-olustur') preview.value = (await previewFaturaRebuild(data.id)).data;
  } catch (e) { error.value = e?.response?.data?.detail || 'Fatura bilgileri yüklenemedi.'; }
  finally { loading.value = false; }
}
onMounted(load);

async function save() {
  if (saving.value || loading.value || !current.value) return;
  if (!neden.value.trim()) { error.value = 'İşlem nedeni zorunludur.'; return; }
  if (props.action === 'yeniden-olustur' && (!preview.value || preview.value.engel)) return;
  saving.value = true;
  error.value = '';
  try {
    const { data } = await correctFatura(current.value.id, props.action, {
      neden: neden.value.trim(), surum: preview.value?.surum ?? current.value.surum,
      ...(preview.value ? { onizleme_anahtari: preview.value.onizleme_anahtari } : {}),
    });
    emit('saved', data);
  } catch (e) {
    const body = e?.response?.data;
    error.value = body?.detail || body?.neden?.[0] || 'İşlem tamamlanamadı. Bilgileri yenileyip tekrar deneyin.';
    current.value = null;
  } finally { saving.value = false; }
}
</script>

<template>
  <Teleport to="body">
    <div class="eisa-modal-backdrop" @click.self="!saving && emit('close')" @keydown.esc="!saving && emit('close')">
      <div class="eisa-modal eisa-modal--medium" role="dialog" aria-modal="true" aria-labelledby="fatura-islem-title">
        <div class="eisa-modal-header">
          <h3 id="fatura-islem-title" class="eisa-modal-title">{{ title }}</h3>
          <button class="eisa-modal-close" title="Kapat" :disabled="saving" @click="emit('close')">×</button>
        </div>
        <div class="eisa-modal-body">
          <p>Fatura #{{ fatura.id }} · {{ fatura.eczane_ad }} · {{ fatura.donem }}</p>
          <p v-if="loading" role="status">Fatura bilgileri yükleniyor…</p>
          <template v-else>
            <p v-if="action === 'iptal'">Fatura borçtan çıkarılır. Fatura ve ödeme geçmişi saklanır. Bu işlem para iadesi yapmaz.</p>
            <p v-else-if="action === 'odemeyi-geri-al'">Hatalı tahsilat kaydı geri alınır ve geçmişte işaretlenir. İptal edilmemiş fatura yeniden borç olarak görünür. Bu işlem bankadan para iadesi yapmaz.</p>
            <template v-else-if="preview">
              <p>Mevcut kalemler güncel sözleşme ve cihaz bedelleriyle yeniden hesaplanır. Fatura numarası, dönem, vade ve taksit sırası korunur; yeni cihaz kalemi eklenmez.</p>
              <dl class="fi-summary">
                <div><dt>Eski tutar</dt><dd>{{ fmt(preview.eski_tutar) }}</dd></div>
                <div><dt>Yeni tutar</dt><dd>{{ fmt(preview.yeni_tutar) }}</dd></div>
                <div><dt>Mevcut tahsilat</dt><dd>{{ fmt(preview.tahsilat) }}</dd></div>
              </dl>
              <p v-if="preview.engel" role="alert">{{ preview.engel }}</p>
              <p v-else>İşlem öncesindeki bilgiler ve gerekçeniz işlem geçmişine kaydedilir.</p>
            </template>
            <label class="eisa-form-row">
              <span class="eisa-field-label">{{ action === 'iptal' ? 'İptal nedeni' : 'İşlem nedeni' }} *</span>
              <textarea v-model="neden" class="eisa-field" rows="3" maxlength="500" required :disabled="saving" placeholder="Düzeltme nedenini açıklayın…"></textarea>
            </label>
          </template>
          <p v-if="error" role="alert">{{ error }}</p>
          <button v-if="!loading && (!current || (action === 'yeniden-olustur' && !preview))" class="eisa-btn eisa-btn-ghost" @click="load">Bilgileri Yenile</button>
        </div>
        <div class="eisa-modal-footer">
          <button class="eisa-btn eisa-btn-ghost" :disabled="saving" @click="emit('close')">Vazgeç</button>
          <button class="eisa-btn eisa-btn-danger" :disabled="loading || saving || !current || !neden.trim() || (action === 'yeniden-olustur' && (!preview || !!preview.engel))" @click="save">
            {{ saving ? 'İşleniyor…' : title }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.fi-summary { display:flex; flex-wrap:wrap; gap:1rem; padding:1rem; background:var(--surface-muted); border:1px solid var(--border-default); border-radius:10px; }
.fi-summary dt { color:var(--text-secondary); font-size:.8rem; }
.fi-summary dd { margin:0; font-weight:700; }
[role="alert"] { color:var(--eisa-red); }
</style>
