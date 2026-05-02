<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { campaigns, showCampaignOverlay, activeCampaignIndex } from '../stores/kiosk.js';
  import { fetchActiveCampaigns } from '../lib/api.js';

  const dispatch = createEventDispatcher();

  const IDLE_TIMEOUT_S = 30;

  let idleSeconds = 0;
  let idleTick;

  $: idleDisplay = `${String(Math.floor(idleSeconds / 60)).padStart(2, '0')}:${String(idleSeconds % 60).padStart(2, '0')}`;
  $: idleOverdue = idleSeconds >= IDLE_TIMEOUT_S;

  function startTimer() {
    idleSeconds = 0;
    clearInterval(idleTick);
    idleTick = setInterval(() => {
      idleSeconds++;
      if (idleSeconds >= IDLE_TIMEOUT_S && $campaigns.length > 0) {
        showCampaignOverlay.set(true);
      }
    }, 1000);
  }

  function handleTap() {
    dispatch('start');
  }

  onMount(async () => {
    startTimer();
    try {
      const list = await fetchActiveCampaigns();
      campaigns.set(list);
    } catch { /* sunucu yoksa kampanya gösterme */ }
  });

  onDestroy(() => clearInterval(idleTick));
</script>

<div
  class="screen screen-idle"
  on:click={handleTap}
  role="button"
  tabindex="0"
  on:keydown={(e) => e.key === 'Enter' && handleTap()}
>
  <div class="idle-bg"></div>

  <div class="idle-timer" class:overdue={idleOverdue}>
    <i class="fa-regular fa-clock"></i>
    {idleDisplay}
  </div>

  <div class="idle-content">
    <div class="idle-logo">e-<span>İSA</span></div>
    <div class="idle-tagline">Eczane İçi Sağlık Asistanınız</div>

    <div class="idle-ad-card">
      <p class="idle-ad-label">ECZANE SAĞLIK KİOSKU</p>
      <p class="idle-ad-text">
        Sağlığınıza önem veriyorsanız,<br>
        <span style="color:#22c55e;">bizimle başlayın.</span>
      </p>
    </div>

    <div class="idle-tap-hint">
      <i class="fa-solid fa-hand-pointer"></i> Başlamak için ekrana dokunun
    </div>
  </div>

  <div class="idle-ad-banner">
    Ekrana dokunarak sağlık danışmanınızla görüşün &nbsp;|&nbsp;
    Bu cihaz yalnızca bilgilendirme amaçlıdır, ilaç tavsiyesi değildir.
  </div>
</div>
