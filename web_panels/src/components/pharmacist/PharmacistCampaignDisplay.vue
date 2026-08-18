<script setup>
/**
 * PharmacistCampaignDisplay — Eczacı paneli kampanya şeridi + idle overlay.
 *
 * - Kampanya şeridi: sayfanın altında sabit, içerik üstüne binmez.
 * - Idle overlay: 90s etkileşimsizlik → aynı kampanya büyük/ortalı gösterilir.
 * - Tek bir shuffle-bag döngüsü her iki yerde kullanılır (iki timer yok).
 * - Sekme gizliyken rotasyon ilerlenmez.
 * - Mevcut açık modal varsa idle ertelenir.
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { http } from '../../services/api';

// ── Sabitler ──────────────────────────────────────────────────────────────────
const FEED_INTERVAL_MS  = 5 * 60 * 1000;  // 5 dakikada bir feed yenile
const IDLE_TIMEOUT_MS   = 90 * 1000;      // 90 saniye
const MOUSEMOVE_THROTTLE_MS = 500;        // mousemove throttle

// ── State ─────────────────────────────────────────────────────────────────────
const campaigns      = ref([]);
const bag            = ref([]);           // shuffle-bag: yeniden karıştırılır bitince
const current        = ref(null);         // o an gösterilen kampanya
const showIdle       = ref(false);

let rotationTimer    = null;
let feedTimer        = null;
let idleTimer        = null;
let lastMouseMove    = 0;

// ── Feed ──────────────────────────────────────────────────────────────────────
async function fetchFeed() {
  try {
    const { data } = await http.get('/api/campaigns/v2/pharmacy-campaigns/feed/');
    const list = Array.isArray(data) ? data : [];
    campaigns.value = list;
    // Feed yenilenince mevcut gösterimi gereksiz kesme:
    // bag'i yalnızca boşaldıysa veya hiç yoksa baştan doldur.
    if (!bag.value.length) refillBag(list);
  } catch {
    // Sessiz hata — mevcut rotasyon korunur
  }
}

// ── Shuffle-bag ───────────────────────────────────────────────────────────────
function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function refillBag(list) {
  if (!list.length) { bag.value = []; return; }
  let shuffled = shuffle(list);
  // Aynı kampanya art arda gelmesin (tek kampanya hariç)
  if (list.length > 1 && current.value && shuffled[0]?.id === current.value.id) {
    shuffled = [...shuffled.slice(1), shuffled[0]];
  }
  bag.value = shuffled;
}

function nextCampaign() {
  if (!campaigns.value.length) { current.value = null; return; }
  if (!bag.value.length) refillBag(campaigns.value);
  current.value = bag.value.shift() ?? null;
}

// ── Rotasyon ──────────────────────────────────────────────────────────────────
function scheduleNext() {
  clearTimeout(rotationTimer);
  if (!current.value) return;
  // Sekme gizliyse programla ama çalıştırma
  rotationTimer = setTimeout(() => {
    if (document.visibilityState === 'hidden') {
      // Sekme görünür olunca devam edecek (visibilitychange handler)
      return;
    }
    nextCampaign();
    scheduleNext();
  }, (current.value.duration_seconds ?? 10) * 1000);
}

function startRotation() {
  if (!campaigns.value.length) { current.value = null; return; }
  if (!current.value) nextCampaign();
  scheduleNext();
}

function stopRotation() {
  clearTimeout(rotationTimer);
}

// ── Idle ──────────────────────────────────────────────────────────────────────
function resetIdleTimer() {
  clearTimeout(idleTimer);
  if (!campaigns.value.length) return;
  idleTimer = setTimeout(() => {
    // Modal açıksa idle'ı ertele
    if (document.querySelector('[role="dialog"], .eisa-modal-backdrop')) {
      resetIdleTimer();
      return;
    }
    showIdle.value = true;
  }, IDLE_TIMEOUT_MS);
}

function dismissIdle() {
  showIdle.value = false;
  resetIdleTimer();
}

// Mouse throttle
function onMouseMove() {
  const now = Date.now();
  if (now - lastMouseMove < MOUSEMOVE_THROTTLE_MS) return;
  lastMouseMove = now;
  if (showIdle.value) dismissIdle();
  else resetIdleTimer();
}

function onActivity() {
  if (showIdle.value) dismissIdle();
  else resetIdleTimer();
}

// ── Visibility API ────────────────────────────────────────────────────────────
function onVisibility() {
  if (document.visibilityState === 'visible') {
    // Sekme tekrar görünür → rotasyonu kaldığı yerden devam ettir
    scheduleNext();
  } else {
    // Sekme gizli → rotasyon durur (setTimeout devam eder ama callback erken çıkar)
    clearTimeout(rotationTimer);
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  await fetchFeed();
  startRotation();
  resetIdleTimer();

  // Feed yenileme
  feedTimer = setInterval(fetchFeed, FEED_INTERVAL_MS);

  // Aktivite dinleyicileri
  window.addEventListener('pointerdown',   onActivity,    { passive: true });
  window.addEventListener('keydown',       onActivity,    { passive: true });
  window.addEventListener('touchstart',    onActivity,    { passive: true });
  window.addEventListener('mousemove',     onMouseMove,   { passive: true });
  document.addEventListener('visibilitychange', onVisibility);
});

onUnmounted(() => {
  stopRotation();
  clearTimeout(idleTimer);
  clearInterval(feedTimer);
  window.removeEventListener('pointerdown',   onActivity);
  window.removeEventListener('keydown',       onActivity);
  window.removeEventListener('touchstart',    onActivity);
  window.removeEventListener('mousemove',     onMouseMove);
  document.removeEventListener('visibilitychange', onVisibility);
});

// Feed değişince rotasyonu yenile (mevcut gösterimi kesme)
watch(campaigns, (list) => {
  if (!list.length) {
    stopRotation();
    current.value = null;
    clearTimeout(idleTimer);
  } else if (!current.value) {
    startRotation();
    resetIdleTimer();
  }
});

const hasContent = computed(() => !!current.value);
</script>

<template>
  <!-- Alt şerit: kampanya yoksa tamamen gizli (boşluk yok) -->
  <div v-if="hasContent" class="pharm-strip">
    <img
      :src="current.media_url"
      :alt="current.name"
      class="pharm-strip-img"
    />
  </div>

  <!-- Idle overlay: z-index modalın altında (modal z-index=60) -->
  <Teleport to="body">
    <div
      v-if="showIdle && hasContent"
      class="pharm-idle-overlay"
      @pointerdown="dismissIdle"
      @keydown="dismissIdle"
      @touchstart="dismissIdle"
      role="button"
      tabindex="0"
      aria-label="Ekrana dokunun"
    >
      <img
        :src="current.media_url"
        :alt="current.name"
        class="pharm-idle-img"
      />
      <p class="pharm-idle-hint">
        <i class="fa-solid fa-hand-pointer"></i> Devam etmek için dokunun
      </p>
    </div>
  </Teleport>
</template>

<style scoped>
/* Alt şerit — flex çocuk olarak sayfa içeriğine eklenir */
.pharm-strip {
  flex-shrink: 0;
  height: 288px;
  background: #111827;
  border-top: 2px solid #B1121B;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.pharm-strip-img {
  height: 100%;
  max-width: 100%;
  object-fit: contain;
}

/* Idle overlay — modalın altında (z-index 40) */
.pharm-idle-overlay {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(17, 24, 39, 0.92);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.5rem;
  cursor: pointer;
  animation: pharm-fade-in 0.3s ease;
}
@keyframes pharm-fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.pharm-idle-img {
  max-width: min(80vw, 720px);
  max-height: 60vh;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 32px 64px rgba(0, 0, 0, 0.6);
}
.pharm-idle-hint {
  color: rgba(255, 255, 255, 0.6);
  font-size: .9rem;
  letter-spacing: .02em;
}
</style>
