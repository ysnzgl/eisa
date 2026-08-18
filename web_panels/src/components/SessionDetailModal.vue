<script setup>
import { ref, watch } from 'vue';
import { http } from '../services/api';
import QrSessionCard from './QrSessionCard.vue';

const props = defineProps({
  /** KioskActivityListSerializer satırı — qr_kodu ve id zorunlu */
  session: { type: Object, default: null },
  /** Admin görünümünde true; tamamlama formu gizlenir */
  readonly: { type: Boolean, default: false },
});
const emit = defineEmits(['close', 'completed']);

const fullSession = ref(null);
const loadError   = ref('');
const loading     = ref(false);

const DURUM_LABEL = {
  COMPLETED: { text: 'Tamamlandı',   cls: 'eisa-pill-success' },
  ABANDONED: { text: 'Terk Edildi',  cls: 'eisa-pill-warning' },
  EXPIRED:   { text: 'Süresi Doldu', cls: 'eisa-pill-danger'  },
};

async function loadFull(qrKodu) {
  if (!qrKodu) return;
  loading.value   = true;
  loadError.value = '';
  fullSession.value = null;
  try {
    const res = await http.get('/api/analytics/sessions/', { params: { qr_kodu: qrKodu } });
    const payload = Array.isArray(res.data)
      ? res.data[0]
      : Array.isArray(res.data?.results)
        ? res.data.results[0]
        : res.data;
    if (!payload) { loadError.value = 'Oturum detayı bulunamadı.'; return; }
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

function onCompleted(updatedSession) {
  fullSession.value = updatedSession;
  emit('completed', updatedSession);
}

function close() { emit('close'); }
</script>

<template>
  <Teleport to="body">
    <div v-if="session" class="eisa-modal-backdrop" @click.self="close">
      <div class="sdm-modal eisa-modal" >

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
          <div id="temelBilgiler" style="margin-top:1rem;display:grid;grid-template-columns:1fr 1fr;gap:0.75rem 1.25rem;">
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
          <div class="eisa-modal-body" style="padding:0;">
            <QrSessionCard
              :session="fullSession"
              :readonly="readonly"
              :durum="session.durum"
              @completed="onCompleted"
            />
          </div>
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
.sdm-modal { display:flex; flex-direction:column; max-width:760px; width:100%; max-height:90vh; background-color:#fff; border-radius:0.5rem; box-shadow:0 0 1rem rgba(0,0,0,0.2); }
</style>
