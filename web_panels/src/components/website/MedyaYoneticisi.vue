<script setup>
/**
 * MedyaYoneticisi — web sitesi medya kütüphanesi (grid, arama, sayfalama,
 * sürükle-bırak çoklu yükleme, alt metin, URL kopyalama, silme).
 *
 * Hem "Medya" sayfasında hem de formlardaki "medya seç" diyaloğunda kullanılır.
 * secimModu=true iken detay panelinde "Bu görseli kullan" butonu çıkar ve
 * çift tıklama doğrudan seçer → emit('sec', medya).
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  listMedya, uploadMedya, updateMedya, deleteMedya, medyaUrl,
} from '../../services/website';
import { humanError } from '../../services/api';
import { medyaDosyaHatasi, IZINLI_MEDYA_TIPLERI, tarihFormat } from '../../lib/websiteForm';
import { useConfirm } from '../../composables/useConfirm.js';

const props = defineProps({
  secimModu: { type: Boolean, default: false },
  seciliId: { type: [Number, String], default: null },
  pageSize: { type: Number, default: 24 },
  /** Açılışta arama kutusuna yazılacak ifade ("Sitede ara" sonucundan gelindiğinde). */
  baslangicArama: { type: String, default: '' },
});
const emit = defineEmits(['sec']);
const { confirm } = useConfirm();

const q = ref(props.baslangicArama || '');
const page = ref(1);
const count = ref(0);
const results = ref([]);
const loading = ref(false);
const surukleniyor = ref(false);
const yuklemeler = ref([]); // { ad, ilerleme, hata, bitti }
const detay = ref(null);
const altMetin = ref('');
const altKaydediliyor = ref(false);
const dosyaInput = ref(null);

const toplamSayfa = computed(() => Math.max(1, Math.ceil(count.value / props.pageSize)));
const accept = IZINLI_MEDYA_TIPLERI.join(',');

async function load() {
  loading.value = true;
  try {
    const data = await listMedya({ q: q.value.trim() || undefined, page: page.value, page_size: props.pageSize });
    count.value = data.count;
    results.value = data.results;
    if (detay.value) {
      detay.value = results.value.find((m) => m.id === detay.value.id) || detay.value;
    }
  } catch { /* interceptor toast gösterir */ } finally {
    loading.value = false;
  }
}

let aramaZamanlayici = null;
watch(q, () => {
  clearTimeout(aramaZamanlayici);
  aramaZamanlayici = setTimeout(() => { page.value = 1; load(); }, 300);
});
watch(page, load);
watch(() => props.baslangicArama, (v) => { q.value = v || ''; });
onMounted(load);
onBeforeUnmount(() => clearTimeout(aramaZamanlayici));

function sayfaGit(p) {
  if (p >= 1 && p <= toplamSayfa.value) page.value = p;
}

// ── Yükleme ─────────────────────────────────────────────────────────────────
async function dosyalariYukle(fileList) {
  const dosyalar = Array.from(fileList || []);
  if (!dosyalar.length) return;
  let basarili = 0;
  let sonYuklenen = null;
  for (const dosya of dosyalar) {
    const hata = medyaDosyaHatasi(dosya);
    const kayit = { ad: dosya.name, ilerleme: 0, hata, bitti: !!hata };
    yuklemeler.value.push(kayit);
    const idx = yuklemeler.value.length - 1;
    if (hata) { toast.error(hata); continue; }
    try {
      sonYuklenen = await uploadMedya(dosya, '', (p) => { yuklemeler.value[idx].ilerleme = p; });
      yuklemeler.value[idx].ilerleme = 100;
      yuklemeler.value[idx].bitti = true;
      basarili += 1;
    } catch (e) {
      const mesaj = e?.response?.data?.dosya?.[0] || humanError(e);
      yuklemeler.value[idx].hata = mesaj;
      yuklemeler.value[idx].bitti = true;
      toast.error(`${dosya.name}: ${mesaj}`);
    }
  }
  if (basarili) {
    toast.success(basarili === 1 ? 'Görsel yüklendi.' : `${basarili} görsel yüklendi.`);
    q.value = '';
    page.value = 1;
    await load();
    if (sonYuklenen) detaySec(results.value.find((m) => m.id === sonYuklenen.id) || sonYuklenen);
  }
  // Başarılı yüklemeleri kısa süre sonra listeden temizle.
  setTimeout(() => { yuklemeler.value = yuklemeler.value.filter((y) => y.hata); }, 2500);
}

function onDrop(e) {
  surukleniyor.value = false;
  dosyalariYukle(e.dataTransfer?.files);
}
function onDragOver(e) {
  if (Array.from(e.dataTransfer?.types || []).includes('Files')) surukleniyor.value = true;
}
function dosyaSecildi(e) {
  dosyalariYukle(e.target.files);
  e.target.value = '';
}

// ── Detay ───────────────────────────────────────────────────────────────────
function detaySec(m) {
  detay.value = m;
  altMetin.value = m?.alt || '';
}

async function altKaydet() {
  if (!detay.value) return;
  altKaydediliyor.value = true;
  try {
    const guncel = await updateMedya(detay.value.id, { alt: altMetin.value.trim() });
    const yeni = { ...detay.value, ...(guncel || {}), alt: guncel?.alt ?? altMetin.value.trim() };
    detay.value = yeni;
    results.value = results.value.map((m) => (m.id === yeni.id ? yeni : m));
    toast.success('Alt metin kaydedildi.');
  } catch { /* toast */ } finally {
    altKaydediliyor.value = false;
  }
}

async function urlKopyala(m) {
  const url = medyaUrl(m.yol);
  const tam = /^https?:/i.test(url) ? url : `${window.location.origin}${url}`;
  try {
    await navigator.clipboard.writeText(tam);
    toast.success('Bağlantı kopyalandı.');
  } catch {
    toast.error('Bağlantı kopyalanamadı.');
  }
}

async function sil(m) {
  const ok = await confirm({
    title: 'Görseli Sil',
    message: `"${m.dosya_adi || m.alt || m.id}" kalıcı olarak silinecek. Kullanıldığı sayfalarda görsel görünmez olur.`,
    confirmLabel: 'Evet, Sil',
    variant: 'danger',
  });
  if (!ok) return;
  try {
    await deleteMedya(m.id);
    toast.success('Görsel silindi.');
    if (detay.value?.id === m.id) detay.value = null;
    if (results.value.length === 1 && page.value > 1) page.value -= 1;
    else await load();
  } catch { /* toast */ }
}

function boyutFormat(b) {
  if (!b && b !== 0) return '—';
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

defineExpose({ load });
</script>

<template>
  <div class="ws-medya" :class="{ 'ws-medya--secim': secimModu }"
    @dragover.prevent="onDragOver" @dragleave.self="surukleniyor = false" @drop.prevent="onDrop">
    <div class="ws-medya-ust">
      <div class="eisa-search-wrap">
        <i class="fa-solid fa-magnifying-glass eisa-search-icon"></i>
        <input v-model="q" class="eisa-field eisa-search-field" placeholder="Dosya adı veya alt metin ara…" />
      </div>
      <button type="button" class="eisa-btn eisa-btn-cta" @click="dosyaInput?.click()">
        <i class="fa-solid fa-cloud-arrow-up"></i> Görsel Yükle
      </button>
      <input ref="dosyaInput" type="file" multiple :accept="accept" hidden @change="dosyaSecildi" />
    </div>

    <div class="ws-dropzone" :class="{ 'is-over': surukleniyor }" @click="dosyaInput?.click()">
      <i class="fa-solid fa-images"></i>
      <span>Görselleri buraya sürükleyip bırakın veya tıklayıp seçin</span>
      <small>JPEG, PNG, WEBP, GIF, AVIF · en fazla 10 MB · SVG kabul edilmez</small>
    </div>

    <ul v-if="yuklemeler.length" class="ws-yukleme-listesi">
      <li v-for="(y, i) in yuklemeler" :key="i" :class="{ 'is-hata': y.hata }">
        <span class="ws-yukleme-ad">{{ y.ad }}</span>
        <span v-if="y.hata" class="ws-yukleme-hata">{{ y.hata }}</span>
        <span v-else class="ws-ilerleme"><span :style="{ width: y.ilerleme + '%' }"></span></span>
        <button v-if="y.hata" type="button" class="eisa-icon-btn" aria-label="Kapat"
          @click="yuklemeler.splice(i, 1)"><i class="fa-solid fa-xmark"></i></button>
      </li>
    </ul>

    <div class="ws-medya-govde">
      <div class="ws-medya-liste">
        <div v-if="loading && !results.length" class="ws-bos"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
        <div v-else-if="!results.length" class="ws-bos">
          <i class="fa-regular fa-image"></i>
          <p>{{ q ? 'Aramaya uygun görsel bulunamadı.' : 'Henüz görsel yüklenmemiş.' }}</p>
        </div>
        <div v-else class="ws-medya-grid" :class="{ 'is-loading': loading }">
          <button v-for="m in results" :key="m.id" type="button" class="ws-medya-kart"
            :class="{ 'is-active': detay?.id === m.id, 'is-secili': seciliId && String(seciliId) === String(m.id) }"
            :title="m.dosya_adi || m.alt" @click="detaySec(m)" @dblclick="secimModu && emit('sec', m)">
            <img :src="medyaUrl(m.yol)" :alt="m.alt || ''" loading="lazy" />
            <span class="ws-medya-kart-ad">{{ m.dosya_adi || m.alt || ('#' + m.id) }}</span>
            <span v-if="!m.alt" class="ws-medya-altyok" title="Alt metin eksik"><i class="fa-solid fa-triangle-exclamation"></i></span>
          </button>
        </div>
        <div v-if="toplamSayfa > 1" class="ws-sayfalama">
          <button type="button" class="eisa-icon-btn" :disabled="page <= 1" aria-label="Önceki sayfa" @click="sayfaGit(page - 1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span>{{ page }} / {{ toplamSayfa }} · {{ count }} görsel</span>
          <button type="button" class="eisa-icon-btn" :disabled="page >= toplamSayfa" aria-label="Sonraki sayfa" @click="sayfaGit(page + 1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>

      <aside v-if="detay" class="ws-medya-detay">
        <div class="ws-medya-detay-gorsel">
          <img :src="medyaUrl(detay.yol)" :alt="detay.alt || ''" />
        </div>
        <dl class="ws-medya-meta">
          <div><dt>Dosya</dt><dd>{{ detay.dosya_adi || '—' }}</dd></div>
          <div><dt>Boyut</dt><dd>{{ boyutFormat(detay.boyut) }}</dd></div>
          <div><dt>Ölçü</dt><dd>{{ detay.genislik && detay.yukseklik ? `${detay.genislik}×${detay.yukseklik}` : '—' }}</dd></div>
          <div><dt>Tür</dt><dd>{{ detay.mime || '—' }}</dd></div>
          <div><dt>Yüklenme</dt><dd>{{ tarihFormat(detay.olusturulma_tarihi) }}</dd></div>
        </dl>
        <label class="eisa-field-label" for="ws-medya-alt">Alt metin (erişilebilirlik / SEO)</label>
        <textarea id="ws-medya-alt" v-model="altMetin" rows="2" maxlength="250" class="eisa-field"
          placeholder="Görseli kısaca tarif edin"></textarea>
        <div class="ws-medya-detay-aksiyon">
          <button type="button" class="eisa-btn eisa-btn--sm" :disabled="altKaydediliyor || altMetin === (detay.alt || '')"
            @click="altKaydet">
            <i class="fa-solid fa-floppy-disk"></i> Alt metni kaydet
          </button>
          <button type="button" class="eisa-btn eisa-btn--sm" @click="urlKopyala(detay)">
            <i class="fa-solid fa-link"></i> URL kopyala
          </button>
          <button type="button" class="eisa-btn eisa-btn--sm ws-btn-tehlike" @click="sil(detay)">
            <i class="fa-solid fa-trash"></i> Sil
          </button>
        </div>
        <button v-if="secimModu" type="button" class="eisa-btn eisa-btn-cta ws-tam" @click="emit('sec', detay)">
          <i class="fa-solid fa-check"></i> Bu görseli kullan
        </button>
      </aside>
    </div>
  </div>
</template>
