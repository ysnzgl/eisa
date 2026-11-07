<script setup>
/**
 * ZenginMetinEditoru — TipTap tabanlı zengin metin (HTML) alanı.
 *
 * Araçlar: H2/H3, kalın, italik, altı çizili, madde/numaralı liste, link,
 * alıntı, tablo (opsiyonel), görsel (gorselEkle=true iken medya kütüphanesinden).
 *
 * Backend `nh3` ile sanitize eder (CONTRACT §5 Blog). `img src` yalnız
 * `/api/media/website/` ile başlamalıdır: editörde görüntüleme için yol
 * API_BASE ile mutlaklaştırılır, emit edilirken tekrar göreli yapılır.
 */
import { onBeforeUnmount, ref, watch } from 'vue';
import { useEditor, EditorContent } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import Image from '@tiptap/extension-image';
import { Table, TableRow, TableCell, TableHeader } from '@tiptap/extension-table';
import { toast } from 'vue-sonner';
import { apiBase, medyaUrl } from '../../services/website';
import { htmlMedyaGoreli, htmlMedyaMutlak, izinliHref } from '../../lib/websiteForm';
import MedyaKutuphanesiDialog from './MedyaKutuphanesiDialog.vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  gorselEkle: { type: Boolean, default: false },
  tablo: { type: Boolean, default: true },
  hatali: { type: Boolean, default: false },
  minYukseklik: { type: String, default: '180px' },
});
const emit = defineEmits(['update:modelValue']);

let sonEmit = props.modelValue || '';
const linkAcik = ref(false);
const linkHref = ref('');
const linkYeniSekme = ref(false);
const medyaAcik = ref(false);

function htmlCikar(ed) {
  const html = ed.isEmpty ? '' : ed.getHTML();
  return htmlMedyaGoreli(html, apiBase());
}

const editor = useEditor({
  content: htmlMedyaMutlak(props.modelValue || '', apiBase()),
  extensions: [
    StarterKit.configure({
      heading: { levels: [2, 3] },
      codeBlock: false,
      link: {
        openOnClick: false,
        autolink: true,
        HTMLAttributes: { rel: 'noopener noreferrer', target: null },
      },
    }),
    Image.configure({ inline: false }),
    Table.configure({ resizable: false }),
    TableRow,
    TableHeader,
    TableCell,
  ],
  onUpdate: ({ editor: ed }) => {
    sonEmit = htmlCikar(ed);
    emit('update:modelValue', sonEmit);
  },
});

watch(() => props.modelValue, (v) => {
  const yeni = v || '';
  if (!editor.value || yeni === sonEmit) return;
  sonEmit = yeni;
  editor.value.commands.setContent(htmlMedyaMutlak(yeni, apiBase()), { emitUpdate: false });
});

onBeforeUnmount(() => editor.value?.destroy());

function c() {
  return editor.value.chain().focus();
}

function linkAc() {
  if (!editor.value) return;
  const attrs = editor.value.getAttributes('link');
  linkHref.value = attrs.href || '';
  linkYeniSekme.value = attrs.target === '_blank';
  linkAcik.value = true;
}
function linkUygula() {
  const href = linkHref.value.trim();
  if (!href) {
    c().extendMarkRange('link').unsetLink().run();
    linkAcik.value = false;
    return;
  }
  if (!izinliHref(href)) {
    toast.warning('Bağlantı /, #, https://, mailto: veya tel: ile başlamalıdır.');
    return;
  }
  c().extendMarkRange('link').setLink({ href, target: linkYeniSekme.value ? '_blank' : null }).run();
  linkAcik.value = false;
}

function gorselSecildi(m) {
  if (!m?.yol) return;
  c().setImage({ src: medyaUrl(m.yol), alt: m.alt || '' }).run();
}

const aktif = (ad, attrs) => !!editor.value?.isActive(ad, attrs);
</script>

<template>
  <div class="ws-zengin" :class="{ 'ws-hatali': hatali }">
    <div v-if="editor" class="ws-zengin-arac" role="toolbar" aria-label="Biçimlendirme">
      <button type="button" :class="{ 'is-active': aktif('heading', { level: 2 }) }" title="Başlık 2"
        @click="c().toggleHeading({ level: 2 }).run()">H2</button>
      <button type="button" :class="{ 'is-active': aktif('heading', { level: 3 }) }" title="Başlık 3"
        @click="c().toggleHeading({ level: 3 }).run()">H3</button>
      <span class="ws-zengin-ayrac"></span>
      <button type="button" :class="{ 'is-active': aktif('bold') }" title="Kalın" aria-label="Kalın"
        @click="c().toggleBold().run()"><i class="fa-solid fa-bold"></i></button>
      <button type="button" :class="{ 'is-active': aktif('italic') }" title="İtalik" aria-label="İtalik"
        @click="c().toggleItalic().run()"><i class="fa-solid fa-italic"></i></button>
      <button type="button" :class="{ 'is-active': aktif('underline') }" title="Altı çizili" aria-label="Altı çizili"
        @click="c().toggleUnderline().run()"><i class="fa-solid fa-underline"></i></button>
      <span class="ws-zengin-ayrac"></span>
      <button type="button" :class="{ 'is-active': aktif('bulletList') }" title="Madde listesi" aria-label="Madde listesi"
        @click="c().toggleBulletList().run()"><i class="fa-solid fa-list-ul"></i></button>
      <button type="button" :class="{ 'is-active': aktif('orderedList') }" title="Numaralı liste" aria-label="Numaralı liste"
        @click="c().toggleOrderedList().run()"><i class="fa-solid fa-list-ol"></i></button>
      <button type="button" :class="{ 'is-active': aktif('blockquote') }" title="Alıntı" aria-label="Alıntı"
        @click="c().toggleBlockquote().run()"><i class="fa-solid fa-quote-left"></i></button>
      <button type="button" :class="{ 'is-active': aktif('link') }" title="Bağlantı" aria-label="Bağlantı"
        @click="linkAc"><i class="fa-solid fa-link"></i></button>
      <button v-if="gorselEkle" type="button" title="Görsel ekle" aria-label="Görsel ekle"
        @click="medyaAcik = true"><i class="fa-regular fa-image"></i></button>
      <template v-if="tablo">
        <span class="ws-zengin-ayrac"></span>
        <button v-if="!aktif('table')" type="button" title="Tablo ekle" aria-label="Tablo ekle"
          @click="c().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"><i class="fa-solid fa-table"></i></button>
        <template v-else>
          <button type="button" title="Satır ekle" @click="c().addRowAfter().run()"><i class="fa-solid fa-grip-lines"></i>+</button>
          <button type="button" title="Sütun ekle" @click="c().addColumnAfter().run()"><i class="fa-solid fa-grip-lines-vertical"></i>+</button>
          <button type="button" title="Satırı sil" @click="c().deleteRow().run()"><i class="fa-solid fa-grip-lines"></i>−</button>
          <button type="button" title="Sütunu sil" @click="c().deleteColumn().run()"><i class="fa-solid fa-grip-lines-vertical"></i>−</button>
          <button type="button" title="Tabloyu sil" @click="c().deleteTable().run()"><i class="fa-solid fa-table"></i>×</button>
        </template>
      </template>
      <span class="ws-zengin-ayrac"></span>
      <button type="button" title="Biçimi temizle" aria-label="Biçimi temizle"
        @click="c().unsetAllMarks().clearNodes().run()"><i class="fa-solid fa-text-slash"></i></button>
      <button type="button" title="Geri al" aria-label="Geri al" :disabled="!editor.can().undo()"
        @click="c().undo().run()"><i class="fa-solid fa-rotate-left"></i></button>
      <button type="button" title="Yinele" aria-label="Yinele" :disabled="!editor.can().redo()"
        @click="c().redo().run()"><i class="fa-solid fa-rotate-right"></i></button>
    </div>

    <div v-if="linkAcik" class="ws-zengin-link">
      <input v-model="linkHref" class="eisa-field" placeholder="https://… , /sayfa veya #bolum"
        @keydown.enter.prevent="linkUygula" @keydown.esc.prevent="linkAcik = false" />
      <label class="eisa-toggle"><input v-model="linkYeniSekme" type="checkbox" /><span>Yeni sekme</span></label>
      <button type="button" class="eisa-btn eisa-btn--sm eisa-btn-cta" @click="linkUygula">Uygula</button>
      <button type="button" class="eisa-btn eisa-btn--sm eisa-btn-ghost" @click="linkAcik = false">Vazgeç</button>
    </div>

    <EditorContent :editor="editor" class="ws-zengin-icerik" :style="{ minHeight: minYukseklik }" />

    <MedyaKutuphanesiDialog v-if="gorselEkle" :open="medyaAcik" baslik="Görsel Ekle"
      @close="medyaAcik = false" @sec="gorselSecildi" />
  </div>
</template>
