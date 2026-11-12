<script setup>
import { computed, ref, watch, onMounted } from 'vue';
import { http, humanError } from '../../services/api';
import { getIslakImzaUrl, downloadGeneratedContract } from '../../services/abonelik';

const props = defineProps({
  sozlesme: { type: Object, required: true },
  approving: { type: Boolean, default: false },
  showApproveButton: { type: Boolean, default: false },
  // 'admin' → /sozlesmeler/{id}/metin, 'eczaci' → /sozlesmelerim/{id}/metin
  role: { type: String, default: 'admin' },
});
const emit = defineEmits(['approve']);

const html = ref('');
const loading = ref(false);
const dondurulmus = ref(false);
const belgeSeti = ref(false);
const belgeTuru = ref('EK1');
const eksikAlanlar = ref([]);
const error = ref('');
const downloading = ref(false);
const official = computed(() => belgeSeti.value || props.sozlesme?.sozlesme_surumu === '2026-EK1');
let requestNumber = 0;

async function fetchMetin() {
  if (!props.sozlesme?.id) return;
  loading.value = true;
  error.value = '';
  const current = ++requestNumber;
  try {
    const url = props.role === 'eczaci'
      ? `/api/abonelik/sozlesmelerim/${props.sozlesme.id}/metin/`
      : `/api/abonelik/sozlesmeler/${props.sozlesme.id}/metin/`;
    const response = official.value || belgeTuru.value !== 'EK1'
      ? await http.get(url, { params: { belge_turu: belgeTuru.value } }) : await http.get(url);
    const { data } = response;
    if (current !== requestNumber) return;
    html.value = data.html || '';
    dondurulmus.value = !!data.dondurulmus;
    belgeSeti.value = !!data.belge_seti;
    eksikAlanlar.value = data.eksik_alanlar || [];
  } catch (e) {
    if (current !== requestNumber) return;
    html.value = ''; error.value = humanError(e);
  } finally { if (current === requestNumber) loading.value = false; }
}

watch(() => props.sozlesme?.id, () => { belgeTuru.value = 'EK1'; fetchMetin(); });
watch(belgeTuru, fetchMetin);
onMounted(fetchMetin);

async function download() {
  downloading.value = true;
  try {
    const { data } = await downloadGeneratedContract(props.sozlesme.id, belgeTuru.value, props.role);
    const href = URL.createObjectURL(data);
    const link = document.createElement('a'); link.href = href;
    link.download = `sozlesme-${props.sozlesme.id}-${belgeTuru.value.toLowerCase()}.docx`;
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000);
  } catch (e) { error.value = humanError(e); } finally { downloading.value = false; }
}

const PRINT_CSS = `
  body { font-family: 'Figtree', Arial, sans-serif; font-size: 10pt; color: #1F2937; line-height: 1.5; padding: 24px; }
  .sz-contract h1 { font-size: 13pt; text-align: center; margin: 0 0 4px; }
  .sz-contract h2 { font-size: 10.5pt; margin: 14px 0 4px; border-bottom: 1px solid #ddd; padding-bottom: 2px; }
  .sz-contract h3 { font-size: 10pt; margin: 10px 0 4px; }
  .sz-head { text-align: center; border-bottom: 2px solid #1F2937; padding-bottom: 8px; margin-bottom: 14px; }
  .sz-no { font-size: 8.5pt; color: #6B7280; }
  .sz-table { width: 100%; border-collapse: collapse; margin: 6px 0; font-size: 9pt; }
  .sz-table th, .sz-table td { border: 1px solid #ddd; padding: 3px 6px; text-align: left; }
  .sz-imza { margin-top: 24px; padding-top: 12px; border-top: 1px dashed #ccc; }
  .sz-imza--onayli { background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 12px; }
  .sz-onay-baslik { color: #065F46; font-weight: 700; font-size: 11pt; }
  .sz-imza-not { font-size: 8pt; color: #6B7280; }
`;

function yazdir() {
  // Ana sayfanın gerçek URL'i kullanılır (about:blank footer olmaz).
  // Geçici bir print container + print-only stylesheet ile sadece sözleşme yazdırılır.
  const style = document.createElement('style');
  style.setAttribute('data-sz-print', '');
  style.textContent = `
    @media print {
      body > *:not(#sz-print-root) { display: none !important; }
      #sz-print-root { display: block !important; }
      @page { margin: 14mm; }
    }
    #sz-print-root { display: none; }
    ${PRINT_CSS}
  `;
  const root = document.createElement('div');
  root.id = 'sz-print-root';
  root.innerHTML = `<div class="sz-contract">${html.value}</div>`;
  document.body.appendChild(style);
  document.body.appendChild(root);

  const cleanup = () => {
    style.remove();
    root.remove();
    window.removeEventListener('afterprint', cleanup);
  };
  window.addEventListener('afterprint', cleanup);
  setTimeout(() => {
    window.print();
    setTimeout(cleanup, 1000);
  }, 100);
}
</script>

<template>
  <div class="sozlesme-matbu">
    <div class="matbu-toolbar">
      <div v-if="official" class="eisa-header-actions matbu-document-tabs"><button class="eisa-btn eisa-btn--sm" :class="belgeTuru === 'EK1' ? 'eisa-btn-cta' : 'eisa-btn-ghost'" @click="belgeTuru = 'EK1'">Ana Sözleşme ve Ek-1</button><button class="eisa-btn eisa-btn--sm" :class="belgeTuru === 'EK2' ? 'eisa-btn-cta' : 'eisa-btn-ghost'" @click="belgeTuru = 'EK2'">Ek-2 Teslim Tutanağı</button></div>
      <span v-if="dondurulmus" class="eisa-pill eisa-pill-success" style="margin-right:auto;">
        <i class="fa-solid fa-lock"></i> Onaylı — değişmez metin
      </span>
      <a v-if="sozlesme.islak_imza_url" :href="getIslakImzaUrl(sozlesme.id)" target="_blank" rel="noopener" class="eisa-btn eisa-btn-ghost">İmzalı Sözleşme / Ek-1</a>
      <a v-if="sozlesme.ek2_islak_imza_url" :href="getIslakImzaUrl(sozlesme.id, 'EK2')" target="_blank" rel="noopener" class="eisa-btn eisa-btn-ghost">İmzalı Ek-2</a>
      <button v-if="official" class="eisa-btn eisa-btn-ghost" :disabled="loading || downloading || !!error" @click="download"><i class="fa-solid fa-file-word"></i>{{ downloading ? 'İndiriliyor…' : 'Word İndir' }}</button>
      <button class="eisa-btn eisa-btn-ghost" :disabled="loading || !!error" @click="yazdir">
        <i class="fa-solid fa-print"></i> Yazdır / PDF
      </button>
    </div>

    <div v-if="loading" class="empty-row">Yükleniyor…</div>
    <div v-else-if="error" class="eisa-error-banner" role="alert">{{ error }}<button class="eisa-btn eisa-btn-ghost eisa-btn--sm" @click="fetchMetin">Tekrar dene</button></div>
    <!-- Backend tarafından güvenli üretilen sözleşme HTML'i -->
    <div v-else class="matbu-body sz-contract" v-html="html"></div>
    <details v-if="official && eksikAlanlar.length" class="matbu-missing"><summary>Elle tamamlanacak alanlar ({{ eksikAlanlar.length }})</summary><ul><li v-for="field in eksikAlanlar" :key="field">{{ field }}</li></ul></details>

    <div v-if="!belgeSeti && showApproveButton && !sozlesme?.eczaci_onay_tarihi" class="matbu-footer">
      <p class="matbu-note">
        Bu sözleşmeyi yukarıdaki tüm maddeleriyle okudum, anladım ve kabul ediyorum.
      </p>
      <button class="eisa-btn eisa-btn-cta" :disabled="approving" @click="emit('approve')">
        <i :class="approving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-signature'"></i>
        {{ approving ? 'Onaylanıyor…' : 'Okudum, Anladım, Onaylıyorum' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.sozlesme-matbu { font-family: 'Figtree', sans-serif; }
.matbu-toolbar { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:.5rem; padding:.5rem 0 .75rem; }
.matbu-document-tabs { margin-right:auto; }
.matbu-missing { margin-top:.8rem; padding:.7rem .9rem; border:1px solid var(--border-default); border-radius:var(--radius-badge); color:var(--text-secondary); font-size:.78rem; }
.matbu-missing summary { cursor:pointer; }
.matbu-body :deep(.sz-official-document) { max-width:900px; margin:0 auto; padding:1rem; background:var(--surface-card); }
.matbu-body :deep(.sz-official-document td) { overflow-wrap:anywhere; vertical-align:top; }
.matbu-body { padding: 0 .25rem; max-height: 55vh; overflow-y: auto; font-size: .85rem; line-height: 1.55; color: #374151; }
.matbu-footer { border-top:1px dashed #E5E7EB; padding-top:1rem; margin-top:1rem; text-align:center; }
.matbu-note { font-size:.82rem; color:#6B7280; line-height:1.5; margin-bottom:.75rem; }

.matbu-body :deep(h1) { font-size:1.05rem; text-align:center; margin:0 0 .3rem; color:#1F2937; }
.matbu-body :deep(h2) { font-size:.85rem; font-weight:700; margin:1rem 0 .3rem; border-bottom:1px solid #E5E7EB; padding-bottom:.2rem; color:#1F2937; }
.matbu-body :deep(h3) { font-size:.82rem; font-weight:700; margin:.75rem 0 .3rem; color:#374151; }
.matbu-body :deep(.sz-head) { text-align:center; border-bottom:2px solid #1F2937; padding-bottom:.75rem; margin-bottom:1rem; }
.matbu-body :deep(.sz-no) { font-size:.72rem; color:#6B7280; }
.matbu-body :deep(p) { margin:.35rem 0; }
.matbu-body :deep(.sz-table) { width:100%; border-collapse:collapse; margin:.5rem 0; font-size:.78rem; }
.matbu-body :deep(.sz-table th), .matbu-body :deep(.sz-table td) { border:1px solid #E5E7EB; padding:.25rem .5rem; text-align:left; }
.matbu-body :deep(.sz-imza) { margin-top:1.25rem; padding-top:.75rem; border-top:1px dashed #D1D5DB; }
.matbu-body :deep(.sz-imza--onayli) { background:#F0FDF4; border:1px solid #86EFAC; border-radius:8px; padding:.75rem; }
.matbu-body :deep(.sz-onay-baslik) { color:#065F46; font-weight:700; font-size:.95rem; }
.matbu-body :deep(.sz-onay-bekliyor) { color:#92400E; font-weight:600; }
.matbu-body :deep(.sz-imza-not) { font-size:.72rem; color:#6B7280; }
</style>
