<script setup>
import { computed, onBeforeUnmount, ref } from 'vue';
import { toast } from 'vue-sonner';
import { http } from '../services/api';

const props = defineProps({
  gorevId: [Number, String],
  dosyalar: { type: Array, default: () => [] },
  disabled: Boolean,
});
const files = defineModel({ type: Array, default: () => [] });
const preview = ref(null);
const busy = ref(false);
const sheetIndex = ref(0);
const sheet = computed(() => preview.value?.sheets?.[sheetIndex.value]);
let requestVersion = 0;

function choose(event) {
  for (const file of event.target.files || []) {
    if (!/\.(pdf|docx?|xlsx?)$/i.test(file.name) || !file.size || file.size > 25 * 1024 * 1024) {
      toast.error(`${file.name}: PDF, Word veya Excel seçin (en fazla 25 MB).`);
      continue;
    }
    files.value = [...files.value, file];
  }
  event.target.value = '';
}

function closePreview() {
  requestVersion++;
  if (preview.value?.url) URL.revokeObjectURL(preview.value.url);
  preview.value = null;
  busy.value = false;
}

async function open(file, download = false) {
  closePreview();
  const version = requestVersion;
  const path = `/api/is-takip/gorevler/${props.gorevId}/dosyalar/${file.id}/`;
  busy.value = true;
  try {
    if (!download && /\.docx$/i.test(file.ad)) {
      const { data } = await http.get(path, { params: { onizleme: 'metin' } });
      if (version === requestVersion) preview.value = { ad: file.ad, paragraphs: data.paragraflar };
      return;
    }
    const { data } = await http.get(path, { responseType: 'blob', params: { indir: download ? '1' : undefined } });
    if (version !== requestVersion) return;
    if (download) {
      const url = URL.createObjectURL(data);
      const link = document.createElement('a');
      link.href = url;
      link.download = file.ad;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } else if (/\.xlsx?$/i.test(file.ad)) {
      const XLSX = await import('xlsx');
      const book = XLSX.read(await data.arrayBuffer(), { type: 'array', sheetRows: 201 });
      const sheets = book.SheetNames.map((name) => {
        const ws = book.Sheets[name];
        const range = ws['!ref'] ? XLSX.utils.decode_range(ws['!ref']) : null;
        if (!range) return { name, rows: [] };
        range.e.r = Math.min(range.e.r, range.s.r + 199);
        range.e.c = Math.min(range.e.c, range.s.c + 49);
        return { name, rows: XLSX.utils.sheet_to_json(ws, { header: 1, raw: false, range, defval: '' }) };
      });
      if (version === requestVersion) {
        sheetIndex.value = 0;
        preview.value = { ad: file.ad, sheets };
      }
    } else if (/\.pdf$/i.test(file.ad)) {
      preview.value = { ad: file.ad, url: URL.createObjectURL(new Blob([data], { type: 'application/pdf' })) };
    }
  } catch {
    toast.error('Dosya açılamadı. Önizleme desteklenmiyorsa indirerek açabilirsiniz.');
  } finally {
    if (version === requestVersion) busy.value = false;
  }
}

onBeforeUnmount(closePreview);
</script>

<template>
  <section class="attachments">
    <span class="eisa-field-label">Dosyalar</span>
    <input type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx" :disabled="disabled" aria-label="İşe dosya ekle" @change="choose" />
    <small class="cell-muted">PDF, Word, Excel · Dosya başına en fazla 25 MB. Seçilen dosyalar Kaydet ile yüklenir.</small>
    <div v-for="(file, index) in files" :key="index" class="attachment">
      <span>{{ file.name }} <small>(yüklenmeyi bekliyor)</small></span>
      <button type="button" class="eisa-btn eisa-btn-ghost" :disabled="disabled" @click="files = files.filter((_, i) => i !== index)">Kaldır</button>
    </div>
    <div v-for="file in dosyalar" :key="file.id" class="attachment">
      <span>{{ file.ad }} <small>({{ (file.boyut / 1024).toLocaleString('tr-TR', { maximumFractionDigits: 1 }) }} KB)</small></span>
      <div class="attachment-actions">
        <button v-if="! /\.doc$/i.test(file.ad)" type="button" class="eisa-btn eisa-btn-ghost" :disabled="busy || disabled" @click="open(file)">Önizle</button>
        <button type="button" class="eisa-btn eisa-btn-ghost" :disabled="busy || disabled" @click="open(file, true)">İndir</button>
      </div>
    </div>
    <p v-if="busy" role="status">Dosya açılıyor…</p>
    <Teleport to="body">
      <div v-if="preview" class="eisa-modal-backdrop document-backdrop" @click.self="closePreview">
        <section class="eisa-modal document-preview" role="dialog" aria-modal="true" :aria-label="preview.ad">
          <div class="eisa-modal-header">
            <h3 class="eisa-modal-title">{{ preview.ad }}</h3>
            <button type="button" class="eisa-btn eisa-btn-ghost" @click="closePreview">Kapat</button>
          </div>
          <div class="eisa-modal-body preview-body">
            <iframe v-if="preview.url" :src="preview.url" :title="preview.ad" />
            <template v-else-if="preview.sheets">
              <p class="cell-muted">Her sayfanın ilk 200 satırı ve 50 sütunu gösterilir. Tam içerik için dosyayı indirin.</p>
              <select v-model="sheetIndex" class="eisa-field" aria-label="Çalışma sayfası">
                <option v-for="(s, i) in preview.sheets" :key="i" :value="i">{{ s.name }}</option>
              </select>
              <div class="sheet-scroll"><table class="eisa-table"><tbody>
                <tr v-for="(row, i) in sheet?.rows" :key="i"><td v-for="(cell, j) in row" :key="j">{{ cell }}</td></tr>
              </tbody></table></div>
            </template>
            <template v-else>
              <p class="cell-muted">Metin önizlemesi; görseller ve sayfa düzeni için dosyayı indirin.</p>
              <p v-for="(paragraph, i) in preview.paragraphs" :key="i" class="document-paragraph">{{ paragraph }}</p>
            </template>
          </div>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.attachments { display: flex; flex-direction: column; gap: .65rem; }
.attachment { display: flex; align-items: center; justify-content: space-between; gap: .5rem; border-bottom: 1px solid #e5e7eb; padding: .4rem 0; }
.attachment > span { overflow-wrap: anywhere; min-width: 0; }
.attachment-actions { display: flex; flex-shrink: 0; }
.document-backdrop { z-index: 12000; }
.document-preview { width: calc(100vw - 2rem); max-width: 1100px; }
.preview-body { overflow: auto; max-height: 78vh; }
.preview-body iframe { width: 100%; height: 70vh; border: 0; }
.sheet-scroll { overflow: auto; max-height: 60vh; }
.document-paragraph { white-space: pre-wrap; overflow-wrap: anywhere; margin: .8rem 0; }
@media (max-width: 600px) { .attachment { align-items: flex-start; flex-direction: column; } }
</style>
