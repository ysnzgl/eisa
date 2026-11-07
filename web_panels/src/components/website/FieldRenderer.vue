<script setup>
/**
 * FieldRenderer — blok şemasındaki tek bir "Alan"ı (CONTRACT §5) dinamik form
 * elemanı olarak çizer. `liste` türünde kendini özyinelemeli (recursive)
 * kullanarak iç içe alanları üretir.
 *
 * Props:
 *   alan       : { ad, etiket, tur, zorunlu, varsayilan, yardim, max_uzunluk,
 *                  secenekler, min, max, alanlar, min_adet, max_adet }
 *   modelValue : alan değeri
 *   hata       : string[] | iç içe hata nesnesi (bkz. lib/websiteForm.js)
 *   yol        : benzersiz id öneki (label/for eşleşmesi için)
 *   veriYolu   : üst veri yolu (ör. "kartlar.1"); kök data-alan-yolu = veriYolu + ad. "Sitede ara"
 *                sonucundan gelinen alanı bulmak için kullanılır (lib/websiteArama.js).
 *
 * Liste düzeyi işlemler (ekle/sil/sırala) yeni dizi emit eder; öğe alanları
 * öğe nesnesi üzerinde yerinde güncellenir (öğe kimliği/odak korunur).
 */
import { computed, inject, reactive, ref, toRaw, watch } from 'vue';
import draggable from 'vuedraggable';
import {
  varsayilanVeri, klonla, hataMesajlari, altHata, hataVarMi, blokOzeti,
} from '../../lib/websiteForm';
import IkonSecici from './IkonSecici.vue';
import MedyaSecici from './MedyaSecici.vue';
import ButonAlani from './ButonAlani.vue';
import ZenginMetinEditoru from './ZenginMetinEditoru.vue';

const props = defineProps({
  alan: { type: Object, required: true },
  modelValue: { type: null, default: undefined },
  hata: { type: [Array, Object, String], default: null },
  yol: { type: String, default: 'alan' },
  veriYolu: { type: String, default: '' },
});
const emit = defineEmits(['update:modelValue']);

const id = computed(() => `${props.yol}-${props.alan.ad}`.replace(/[^a-zA-Z0-9_-]/g, '-'));
const tamYol = computed(() => (props.veriYolu ? `${props.veriYolu}.${props.alan.ad}` : props.alan.ad));
// Arama hedefi (SayfaEditoru provide eder): hedef bu listenin bir öğesindeyse öğe açılır.
const hedefYol = inject('wsHedefYol', ref(''));
const mesajlar = computed(() => hataMesajlari(props.hata));
const hataVar = computed(() => hataVarMi(props.hata));
const tur = computed(() => props.alan.tur);

function guncelle(v) {
  emit('update:modelValue', v);
}

// ── metin / uzun_metin ───────────────────────────────────────────────────────
const uzunluk = computed(() => String(props.modelValue ?? '').length);

// ── sayi ─────────────────────────────────────────────────────────────────────
function sayiGuncelle(e) {
  const v = e.target.value;
  guncelle(v === '' ? null : Number(v));
}

// ── secim ────────────────────────────────────────────────────────────────────
const secenekler = computed(() => props.alan.secenekler || []);
const segmentli = computed(() => secenekler.value.length > 0 && secenekler.value.length <= 4);
function secimGuncelle(e) {
  const s = secenekler.value[e.target.selectedIndex - (props.alan.zorunlu ? 0 : 1)];
  guncelle(s ? s.deger : '');
}
const seciliIndeks = computed(() => secenekler.value.findIndex((s) => String(s.deger) === String(props.modelValue)));

// ── liste ────────────────────────────────────────────────────────────────────
const anahtarlar = new WeakMap();
let sayac = 0;
function ogeAnahtari(oge) {
  const ham = toRaw(oge);
  if (!ham || typeof ham !== 'object') return `p-${sayac++}`;
  if (!anahtarlar.has(ham)) anahtarlar.set(ham, `o-${++sayac}`);
  return anahtarlar.get(ham);
}

const dizi = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []));
watch(() => [tur.value, props.modelValue], () => {
  if (tur.value === 'liste' && !Array.isArray(props.modelValue)) guncelle([]);
}, { immediate: true });

const maxAdet = computed(() => props.alan.max_adet || null);
const minAdet = computed(() => props.alan.min_adet || 0);
const eklenebilir = computed(() => !maxAdet.value || dizi.value.length < maxAdet.value);
const silinebilir = computed(() => dizi.value.length > minAdet.value);

const acikOgeler = reactive(new Set());
// Az öğe varsa hepsi açık başlar; çoksa kapalı (hatalı olanlar her zaman açık).
watch(() => tur.value === 'liste' && dizi.value.length, () => {
  if (tur.value !== 'liste') return;
  if (!acikOgeler.size && dizi.value.length <= 2) dizi.value.forEach((o) => acikOgeler.add(ogeAnahtari(o)));
}, { immediate: true });

watch(() => [hedefYol.value, dizi.value.length], ([hedef]) => {
  if (tur.value !== 'liste' || !hedef) return;
  dizi.value.forEach((oge, i) => {
    const oy = `${tamYol.value}.${i}`;
    if (hedef === oy || hedef.startsWith(`${oy}.`)) acikOgeler.add(ogeAnahtari(oge));
  });
}, { immediate: true });

function ogeAcik(oge, i) {
  return acikOgeler.has(ogeAnahtari(oge)) || hataVarMi(altHata(props.hata, i));
}
function ogeToggle(oge) {
  const k = ogeAnahtari(oge);
  if (acikOgeler.has(k)) acikOgeler.delete(k); else acikOgeler.add(k);
}
function ogeEkle() {
  if (!eklenebilir.value) return;
  const yeni = varsayilanVeri(props.alan.alanlar || []);
  acikOgeler.add(ogeAnahtari(yeni));
  guncelle([...dizi.value, yeni]);
}
function ogeKopyala(i) {
  if (!eklenebilir.value) return;
  const kopya = klonla(dizi.value[i]);
  acikOgeler.add(ogeAnahtari(kopya));
  const yeni = [...dizi.value];
  yeni.splice(i + 1, 0, kopya);
  guncelle(yeni);
}
function ogeSil(i) {
  if (!silinebilir.value) return;
  const yeni = [...dizi.value];
  yeni.splice(i, 1);
  guncelle(yeni);
}
function ogeTasi(i, yon) {
  const j = i + yon;
  if (j < 0 || j >= dizi.value.length) return;
  const yeni = [...dizi.value];
  [yeni[i], yeni[j]] = [yeni[j], yeni[i]];
  guncelle(yeni);
}
function ogeAlanGuncelle(oge, ad, v) {
  oge[ad] = v;
  guncelle(dizi.value);
}
function ogeOzeti(oge) {
  return blokOzeti(oge, { alanlar: props.alan.alanlar }, 50);
}
// Liste düzeyi mesajlar: hem [".."] hem { _genel: [..] } biçimi.
const listeGenelHata = computed(() => hataMesajlari(props.hata));
</script>

<template>
  <div class="ws-alan" :class="[`ws-alan--${tur}`, { 'ws-alan--hatali': hataVar }]" :data-alan="alan.ad" :data-alan-yolu="tamYol">
    <!-- Etiket (bool kendi etiketini taşır) -->
    <div v-if="tur !== 'bool'" class="ws-alan-ust">
      <label class="eisa-field-label" :for="id">
        {{ alan.etiket || alan.ad }}<span v-if="alan.zorunlu" class="ws-zorunlu" aria-hidden="true">*</span>
      </label>
      <span v-if="(tur === 'metin' || tur === 'uzun_metin') && alan.max_uzunluk" class="ws-sayac"
        :class="{ 'is-asim': uzunluk > alan.max_uzunluk }">{{ uzunluk }}/{{ alan.max_uzunluk }}</span>
      <span v-if="tur === 'liste'" class="ws-sayac">
        {{ dizi.length }}<template v-if="maxAdet"> / {{ maxAdet }}</template> öğe
      </span>
    </div>

    <!-- metin -->
    <input v-if="tur === 'metin'" :id="id" class="eisa-field" :class="{ 'ws-hatali': hataVar }" type="text"
      :value="modelValue ?? ''" :maxlength="alan.max_uzunluk || undefined" :required="alan.zorunlu"
      @input="guncelle($event.target.value)" />

    <!-- uzun_metin -->
    <textarea v-else-if="tur === 'uzun_metin'" :id="id" class="eisa-field ws-textarea" :class="{ 'ws-hatali': hataVar }"
      rows="4" :value="modelValue ?? ''" :maxlength="alan.max_uzunluk || undefined" :required="alan.zorunlu"
      @input="guncelle($event.target.value)"></textarea>

    <!-- zengin_metin -->
    <ZenginMetinEditoru v-else-if="tur === 'zengin_metin'" :model-value="modelValue ?? ''" gorsel-ekle
      :hatali="hataVar" @update:model-value="guncelle" />

    <!-- sayi -->
    <input v-else-if="tur === 'sayi'" :id="id" class="eisa-field ws-sayi" :class="{ 'ws-hatali': hataVar }"
      type="number" step="any" :min="alan.min ?? undefined" :max="alan.max ?? undefined"
      :value="modelValue ?? ''" @input="sayiGuncelle" />

    <!-- bool -->
    <label v-else-if="tur === 'bool'" class="eisa-toggle ws-bool" :for="id">
      <input :id="id" type="checkbox" :checked="!!modelValue" @change="guncelle($event.target.checked)" />
      <span>{{ alan.etiket || alan.ad }}</span>
    </label>

    <!-- secim -->
    <template v-else-if="tur === 'secim'">
      <div v-if="segmentli" class="ws-segment" role="radiogroup" :aria-label="alan.etiket">
        <button v-for="s in secenekler" :key="String(s.deger)" type="button" role="radio"
          :aria-checked="String(s.deger) === String(modelValue)"
          :class="{ 'is-active': String(s.deger) === String(modelValue) }" @click="guncelle(s.deger)">
          {{ s.etiket }}
        </button>
      </div>
      <select v-else :id="id" class="eisa-field" :class="{ 'ws-hatali': hataVar }" @change="secimGuncelle">
        <option v-if="!alan.zorunlu" value="" :selected="seciliIndeks < 0">— Seçilmedi —</option>
        <option v-for="(s, i) in secenekler" :key="String(s.deger)" :selected="i === seciliIndeks">{{ s.etiket }}</option>
      </select>
    </template>

    <!-- ikon -->
    <IkonSecici v-else-if="tur === 'ikon'" :model-value="modelValue || ''" :zorunlu="alan.zorunlu" :hatali="hataVar"
      @update:model-value="guncelle" />

    <!-- medya -->
    <MedyaSecici v-else-if="tur === 'medya'" :model-value="modelValue || null" :hatali="hataVar"
      @update:model-value="guncelle" />

    <!-- buton -->
    <ButonAlani v-else-if="tur === 'buton'" :model-value="modelValue" :hata="hata" :id-onek="id" :zorunlu="alan.zorunlu"
      @update:model-value="guncelle" />

    <!-- liste -->
    <div v-else-if="tur === 'liste'" class="ws-liste">
      <draggable :model-value="dizi" :item-key="ogeAnahtari" handle=".ws-tutamac" :animation="150"
        ghost-class="ws-surukle-hayalet" class="ws-liste-ogeler" @update:model-value="guncelle">
        <template #item="{ element: oge, index: i }">
          <div class="ws-liste-oge" :class="{ 'is-hatali': hataVarMi(altHata(hata, i)) }">
            <div class="ws-liste-oge-ust">
              <span class="ws-tutamac" title="Sürükleyerek sırala" aria-hidden="true"><i class="fa-solid fa-grip-vertical"></i></span>
              <button type="button" class="ws-liste-oge-baslik" :aria-expanded="ogeAcik(oge, i)" @click="ogeToggle(oge)">
                <i class="fa-solid" :class="ogeAcik(oge, i) ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                <strong>#{{ i + 1 }}</strong>
                <span class="ws-liste-oge-ozet">{{ ogeOzeti(oge) || 'Boş öğe' }}</span>
                <i v-if="hataVarMi(altHata(hata, i))" class="fa-solid fa-circle-exclamation ws-hata-ikon"></i>
              </button>
              <div class="ws-liste-oge-aksiyon">
                <button type="button" class="eisa-icon-btn" title="Yukarı taşı" aria-label="Yukarı taşı" :disabled="i === 0"
                  @click="ogeTasi(i, -1)"><i class="fa-solid fa-arrow-up"></i></button>
                <button type="button" class="eisa-icon-btn" title="Aşağı taşı" aria-label="Aşağı taşı"
                  :disabled="i === dizi.length - 1" @click="ogeTasi(i, 1)"><i class="fa-solid fa-arrow-down"></i></button>
                <button type="button" class="eisa-icon-btn" title="Kopyala" aria-label="Kopyala" :disabled="!eklenebilir"
                  @click="ogeKopyala(i)"><i class="fa-regular fa-copy"></i></button>
                <button type="button" class="eisa-icon-btn danger" title="Sil" aria-label="Sil" :disabled="!silinebilir"
                  @click="ogeSil(i)"><i class="fa-solid fa-trash"></i></button>
              </div>
            </div>
            <div v-show="ogeAcik(oge, i)" class="ws-liste-oge-govde">
              <FieldRenderer v-for="alt in alan.alanlar || []" :key="alt.ad" :alan="alt" :model-value="oge[alt.ad]"
                :hata="altHata(altHata(hata, i), alt.ad)" :yol="`${id}-${i}`" :veri-yolu="`${tamYol}.${i}`"
                @update:model-value="(v) => ogeAlanGuncelle(oge, alt.ad, v)" />
            </div>
          </div>
        </template>
      </draggable>
      <p v-if="!dizi.length" class="ws-bos-mini">Henüz öğe yok.</p>
      <button type="button" class="eisa-btn eisa-btn--sm ws-liste-ekle" :disabled="!eklenebilir" @click="ogeEkle">
        <i class="fa-solid fa-plus"></i> Öğe ekle
        <span v-if="!eklenebilir" class="ws-sayac">(en fazla {{ maxAdet }})</span>
      </button>
      <p v-for="m in listeGenelHata" :key="m" class="ws-alan-hata">{{ m }}</p>
    </div>

    <p v-else class="ws-alan-hata">Desteklenmeyen alan türü: {{ tur }}</p>

    <p v-if="alan.yardim" class="ws-yardim">{{ alan.yardim }}</p>
    <p v-else-if="tur === 'uzun_metin'" class="ws-yardim">Satır sonları korunur; boş satır yeni paragraf başlatır.</p>
    <template v-if="tur !== 'liste' && tur !== 'buton'">
      <p v-for="m in mesajlar" :key="m" class="ws-alan-hata">{{ m }}</p>
    </template>
  </div>
</template>
