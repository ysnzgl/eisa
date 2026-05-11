<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { campaigns } from '../stores/kiosk.js';
  import { fetchActiveCampaigns } from '../lib/api.js';

  const dispatch = createEventDispatcher();
  const SS_TIMEOUT = 10; // saniye — ekran koruyucu başlatma süresi

  // Screensaver için yedek görseller (kampanya yoksa)
  const DUMMY_IMAGES = [
    'https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=794&h=1123&fit=crop',
    'https://images.unsplash.com/photo-1628771065518-0d82f1938462?w=794&h=1123&fit=crop',
    'https://images.unsplash.com/photo-1543362906-acfc16c67564?w=794&h=1123&fit=crop',
  ];

  let idleTick;
  let screensaver = false;
  let ssIndex = 0;
  let ssTick;
  let ssVisible = true;

  $: ssImages = $campaigns.length > 0
    ? $campaigns.map(c => c.media_url).filter(Boolean)
    : DUMMY_IMAGES;

  $: ssImage = ssImages[ssIndex % Math.max(ssImages.length, 1)];

  function startIdleTimer() {
    screensaver = false;
    clearInterval(idleTick);
    clearInterval(ssTick);
    idleTick = setTimeout(() => enterScreensaver(), SS_TIMEOUT * 1000);
  }

  function enterScreensaver() {
    screensaver = true;
    ssIndex = 0;
    ssVisible = true;
    clearInterval(ssTick);
    ssTick = setInterval(() => {
      ssVisible = false;
      setTimeout(() => {
        ssIndex = (ssIndex + 1) % ssImages.length;
        ssVisible = true;
      }, 600);
    }, 5000);
  }

  function handleTap() {
    clearTimeout(idleTick);
    clearInterval(ssTick);
    dispatch('start');
  }

  onMount(async () => {
    startIdleTimer();
    try {
      const list = await fetchActiveCampaigns();
      campaigns.set(list);
    } catch { /* offline */ }
  });

  onDestroy(() => {
    clearTimeout(idleTick);
    clearInterval(ssTick);
  });
</script>

{#if screensaver}
  <!-- ── Ekran Koruyucu ── -->
  <div
    class="screen-saver"
    on:click={handleTap}
    role="button"
    tabindex="0"
    on:keydown={(e) => e.key === 'Enter' && handleTap()}
  >
    <div class="ss-bg-layer" style="opacity:{ssVisible ? 1 : 0}">
      {#if ssImage && /\.(mp4|webm|ogg)$/i.test(ssImage)}
        <!-- svelte-ignore a11y-media-has-caption -->
        <video src={ssImage} autoplay loop muted playsinline class="ss-media"></video>
      {:else if ssImage}
        <img src={ssImage} alt="ekran koruyucu" class="ss-media" />
      {:else}
        <div class="ss-css-bg"></div>
      {/if}
    </div>

    <div class="ss-overlay-text">
      <div class="ss-logo">e-<span>İSA</span></div>
      <div class="ss-sub">Eczane İçi Sağlık Asistanınız</div>
      <div class="ss-tap">
        <i class="fa-solid fa-hand-pointer ss-pulse-icon"></i>
        Başlamak için dokunun
      </div>
    </div>
  </div>

{:else}
  <!-- ── Normal Bekleme ── -->
  <div
    class="screen screen-idle"
    on:click={handleTap}
    role="button"
    tabindex="0"
    on:keydown={(e) => e.key === 'Enter' && handleTap()}
  >
    <div class="idle-bg"></div>

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
{/if}

