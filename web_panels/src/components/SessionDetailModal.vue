<script setup>
import { ref, watch } from 'vue';
import { http } from '../services/api';
import { completeSession } from '../services/analytics';

const props = defineProps({
  /** KioskActivityListSerializer satırı — qr_kodu ve id zorunlu */
  session: { type: Object, default: null },
  /** Admin görünümünde true; tamamlama formu gizlenir */
  readonly: { type: Boolean, default: false },
});
const emit = defineEmits(['close', 'completed']);

const fullSession  = ref(null);
const loadError    = ref('');
const loading      = ref(false);
const completionNote    = ref('');
const completionLoading = ref(false);
const completionError   = ref('');

const GENDER_LABEL = { F: 'Kadın', M: 'Erkek', O: 'Diğer', male: 'Erkek', female: 'Kadın' };
const DURUM_LABEL  = {
  COMPLETED: { text: 'Tamamlandı',   cls: 'eisa-pill-success' },
  ABANDONED: { text: 'Terk Edildi',  cls: 'eisa-pill-warning' },
  EXPIRED:   { text: 'Süresi Doldu', cls: 'eisa-pill-danger'  },
};

function fmtDT(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

async function loadFull(qrKodu) {
  if (!qrKodu) return;
  loading.value   = true;
  loadError.value = '';
  fullSession.value = null;
  completionNote.value  = '';
  completionError.value = '';
  try {
    const res = await http.get('/api/analytics/sessions/', { params: { qr_kodu: qrKodu } });
    const payload = Array.isArray(res.data)
      ? res.data[0]
      : Array.isArray(res.data?.results)
        ? res.data.results[0]
        : res.data;
    if (!payload) {
      loadError.value = 'Oturum detayı bulunamadı.';
      return;
    }
    fullSession.value = payload;
  } catch (err) {
    const st = err?.response?.status;
    loadError.value = (st === 403 || st === 404)
      ? 'Bu oturuma erişim yetkiniz yok veya oturum bulunamadı.'
      : 'Oturum detayı yüklenemedi.';
  } finally {
    loading.value = false;
  }
}

watch(() => props.session, (val) => {
  if (val?.qr_kodu) loadFull(val.qr_kodu);
}, { immediate: true });

async function handleComplete(saleResult) {
  if (!fullSession.value?.id || completionLoading.value) return;
  completionLoading.value = true;
  completionError.value   = '';
  try {
    const res = await completeSession(fullSession.value.id, completionNote.value, saleResult);
    fullSession.value = { ...fullSession.value, ...res.data };
    emit('completed', fullSession.value);
  } catch (err) {
    completionError.value =
      err?.response?.data?.detail || 'Danışma tamamlanırken bir hata oluştu.';
  } finally {
    completionLoading.value = false;
  }
}

function close() { emit('close'); }
</script>

<template>
  <Teleport to="body">
    <div v-if="session" class="eisa-modal-backdrop" @click.self="close">
      <div class="sdm-modal eisa-modal" style="max-width:560px;overflow-y:auto;">

        <!-- Header -->
        <div class="eisa-modal-header">
          <h3 style="display:flex;align-items:center;gap:0.5rem;">
            <i class="fa-solid fa-qrcode" style="color:#0D9488;"></i>
            QR Oturum Detayı
          </h3>
          <button class="eisa-modal-close" @click="close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <!-- Loading -->
        <div v-if="loading" style="padding:3rem;text-align:center;color:#6B7280;">
          <i class="fa-solid fa-circle-notch fa-spin" style="font-size:1.5rem;"></i>
        </div>

        <!-- Error -->
        <div v-else-if="loadError" style="padding:1.5rem;">
          <div class="eisa-error-banner">
            <i class="fa-solid fa-triangle-exclamation"></i> {{ loadError }}
          </div>
          <!-- Fallback: list row verisiyle temel bilgi göster -->
          <div style="margin-top:1rem;display:grid;grid-template-columns:1fr 1fr;gap:0.75rem 1.25rem;">
            <div>
              <p style="font-size:0.7rem;color:#9CA3AF;">QR Kodu</p>
              <p style="font-family:'DM Mono',monospace;font-weight:700;">{{ session.qr_kodu }}</p>
            </div>
            <div>
              <p style="font-size:0.7rem;color:#9CA3AF;">Durum</p>
              <span class="eisa-pill" :class="DURUM_LABEL[session.durum]?.cls || 'eisa-pill-muted'">
                {{ DURUM_LABEL[session.durum]?.text || session.durum }}
              </span>
            </div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Kiosk</p><p>{{ session.kiosk_ad || '—' }}</p></div>
            <div><p style="font-size:0.7rem;color:#9CA3AF;">Eczane</p><p>{{ session.eczane_adi || '—' }}</p></div>
          </div>
        </div>

        <!-- Full session detail -->
        <template v-else-if="fullSession">
          <div class="eisa-modal-body sdm-body">

            <!-- QR + Durum başlık satırı -->
            <div class="sdm-header-row">
              <div>
                <p class="sdm-label">QR Kodu</p>
                <p class="sdm-mono">{{ fullSession.qr_kodu }}</p>
              </div>
              <div style="text-align:right;">
                <p class="sdm-label">Durum</p>
                <!-- durum OturumLoguSerializer'da yok; liste satırından alınır -->
              <span class="eisa-pill" :class="DURUM_LABEL[session.durum]?.cls || 'eisa-pill-muted'">
                  {{ DURUM_LABEL[session.durum]?.text || session.durum }}
                </span>
              </div>
            </div>

            <!-- Hassas uyarı -->
            <div v-if="fullSession.hassas_akis" class="sdm-sensitive-bar">
              <i class="fa-solid fa-triangle-exclamation"></i>
              Hassas Konu — Hasta bu konuyu kalabalık içinde söylemek istemedi.
            </div>

            <!-- Grid: Demografik + kiosk bilgi -->
            <div class="sdm-grid">
              <div><p class="sdm-label">Yaş Aralığı</p>
                <p class="sdm-val">{{ fullSession.yas_araligi_detay?.ad || fullSession.yas_araligi_ad || '—' }}</p></div>
              <div><p class="sdm-label">Cinsiyet</p>
                <p class="sdm-val">{{ fullSession.cinsiyet_detay?.ad || GENDER_LABEL[fullSession.cinsiyet_kod] || fullSession.cinsiyet_ad || '—' }}</p></div>
              <div><p class="sdm-label">İşlem Türü</p>
                <p class="sdm-val">{{ fullSession.oturum_tipi === 'OZEL_DANISMANLIK' ? 'Özel Danışmanlık' : 'Şikayet' }}</p></div>
              <div><p class="sdm-label">Kategori</p>
                <p class="sdm-val">
                  <template v-if="fullSession.oturum_tipi === 'OZEL_DANISMANLIK'">
                    {{ fullSession.danisma_kategorisi_detay?.ad || fullSession.danisma_kategorisi_adi || '—' }}
                  </template>
                  <template v-else>
                    {{ fullSession.kategori_detay?.ad || fullSession.kategori_adi || '—' }}
                  </template>
                </p></div>
              <div><p class="sdm-label">Kiosk</p>
                <p class="sdm-val">{{ fullSession.kiosk_ad || fullSession.kiosk_detay?.ad || '—' }}</p></div>
              <div><p class="sdm-label">Eczane</p>
                <p class="sdm-val">{{ fullSession.eczane_adi || fullSession.eczane?.ad || '—' }}</p></div>
              <div style="grid-column:1/span 2;"><p class="sdm-label">Tarih</p>
                <p class="sdm-val">{{ fmtDT(fullSession.olusturulma_tarihi) }}</p></div>
            </div>

            <!-- Soru & Cevaplar -->
            <div v-if="fullSession.cevap_detaylari?.length" class="sdm-section">
              <p class="sdm-section-title">Soru ve Cevaplar</p>
              <ol class="sdm-qa-list">
                <li v-for="item in fullSession.cevap_detaylari"
                    :key="`${item.soru_id}-${item.cevap_id}`">
                  <strong>{{ item.soru_metni }}</strong>
                  <div style="color:#4B5563;margin-top:0.2rem;">{{ item.cevap_metni }}</div>
                </li>
              </ol>
            </div>

            <!-- Önerilen Etken Maddeler -->
            <div v-if="fullSession.onerilen_etken_madde_detaylari?.length || fullSession.onerilen_etken_maddeler?.length"
                 class="sdm-section">
              <p class="sdm-section-title">Önerilen Etken Maddeler</p>
              <div style="display:flex;flex-wrap:wrap;gap:0.5rem;">
                <span
                  v-for="ing in (fullSession.onerilen_etken_madde_detaylari?.length
                    ? fullSession.onerilen_etken_madde_detaylari
                    : (fullSession.onerilen_etken_maddeler || []).map((v) => ({ id: v?.id || v, ad: v?.ad || v })))"
                  :key="ing.id || ing.ad"
                  class="eisa-pill eisa-pill-info"
                >{{ ing.ad }}</span>
              </div>
            </div>

            <!-- Danışma tamamlandı bilgisi -->
            <div v-if="fullSession.danisma_tamamlandi" class="sdm-section sdm-complete-info">
              <div style="display:flex;align-items:center;gap:0.5rem;color:#10B981;font-weight:600;margin-bottom:0.4rem;">
                <i class="fa-solid fa-check-circle"></i> Danışma Tamamlandı
              </div>
              <p v-if="fullSession.danisma_notu" style="font-size:0.85rem;color:#374151;margin-bottom:0.3rem;">
                <strong>Eczacı Notu:</strong> {{ fullSession.danisma_notu }}
              </p>
              <p style="font-size:0.8rem;color:#6B7280;">
                {{ fullSession.danisma_tamamlayan_eczaci_adi || '—' }} tarafından
                {{ fmtDT(fullSession.danisma_tamamlanma_tarihi) }} tarihinde tamamlandı.
              </p>
            </div>

            <!-- Tamamlama formu — yalnız eczacı (readonly=false) ve henüz tamamlanmamışsa -->
            <div v-if="!readonly && !fullSession.danisma_tamamlandi && fullSession.tamamlandi"
                 class="sdm-section sdm-complete-action">
              <p class="sdm-label" style="margin-bottom:0.5rem;">Danışma Notu (Opsiyonel)</p>
              <textarea
                v-model="completionNote"
                rows="2"
                placeholder="Hastaya verilen tavsiye veya önerilen etken maddeler..."
                class="eisa-field"
                style="margin-bottom:0.75rem;"
              ></textarea>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
                <button class="eisa-btn eisa-btn-success" :disabled="completionLoading"
                        @click="handleComplete('sold')">
                  <i v-if="completionLoading" class="fa-solid fa-circle-notch fa-spin"></i>
                  <i v-else class="fa-solid fa-check"></i>
                  Satış Yaptım
                </button>
                <button class="eisa-btn eisa-btn-ghost" :disabled="completionLoading"
                        @click="handleComplete('not_sold')">
                  <i v-if="completionLoading" class="fa-solid fa-circle-notch fa-spin"></i>
                  <i v-else class="fa-solid fa-xmark"></i>
                  Satış Yapmadım
                </button>
              </div>
              <p v-if="completionError" class="eisa-error-text" style="margin-top:0.5rem;text-align:center;">
                {{ completionError }}
              </p>
            </div>

            <!-- Tamamlanmamış & abandoned/expired uyarısı -->
            <div v-if="!readonly && !fullSession.danisma_tamamlandi && !fullSession.tamamlandi"
                 style="padding:0.75rem;background:rgba(245,158,11,0.08);border-radius:6px;border:1px solid rgba(245,158,11,0.2);font-size:0.82rem;color:#D97706;">
              <i class="fa-solid fa-circle-info" style="margin-right:0.4rem;"></i>
              Hasta oturumu tamamlamadığı için danışma yapılamıyor.
            </div>

          </div><!-- /eisa-modal-body -->
        </template>

        <!-- Footer -->
        <div class="eisa-modal-footer">
          <button class="eisa-btn eisa-btn-ghost" @click="close">Kapat</button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.sdm-modal { display:flex; flex-direction:column; }
.sdm-body  { padding:1.25rem 1.5rem; display:flex; flex-direction:column; gap:1rem; }

.sdm-header-row {
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  padding-bottom:0.75rem;
  border-bottom:1px solid rgba(255,255,255,0.06);
}

.sdm-label { font-size:0.7rem; color:#9CA3AF; margin-bottom:0.15rem; }
.sdm-val   { font-size:0.9rem; color:#111827; }
.sdm-mono  { font-family:'DM Mono',monospace; font-weight:700; font-size:1.1rem; letter-spacing:0.08em; color:#111827; }

.sdm-sensitive-bar {
  display:flex; align-items:center; gap:0.5rem;
  padding:0.6rem 0.85rem;
  background:rgba(245,158,11,0.1);
  border:1px solid rgba(245,158,11,0.3);
  border-radius:6px;
  font-size:0.82rem;
  color:#D97706;
  font-weight:500;
}

.sdm-grid {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:0.65rem 1.25rem;
}

.sdm-section { display:flex; flex-direction:column; gap:0.4rem; }
.sdm-section-title { font-size:0.75rem; color:#9CA3AF; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; }

.sdm-qa-list {
  margin:0; padding-left:1.2rem;
  display:grid; gap:0.5rem;
  font-size:0.85rem; color:#111827;
}

.sdm-complete-info {
  padding:0.85rem 1rem;
  background:rgba(16,185,129,0.06);
  border:1px solid rgba(16,185,129,0.2);
  border-radius:8px;
}

.sdm-complete-action {
  padding:0.85rem 1rem;
  background:rgba(13,148,136,0.05);
  border:1px solid rgba(13,148,136,0.2);
  border-radius:8px;
}
</style>
