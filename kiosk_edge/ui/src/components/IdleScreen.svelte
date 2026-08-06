<script>
  // Cekici (attractor) / bekleme ekrani.
  //   paid mod  : ucretli creative tam ekran, AdPromo gorunmez.
  //   house_ad  : HouseAd gorseli tam ekran, AdPromo alt overlay.
  //   fallback  : icerik yok, yerel guvenli arka plan + alt AdPromo overlay.
  // AdPromo hicbir modda tam ekran arka plan olarak kullanilmaz.
  import { createEventDispatcher, onDestroy } from 'svelte';
  import { campaigns, playlistItems } from '../stores/kiosk.js';
  import Logo from './Logo.svelte';
  import AdPromo from './AdPromo.svelte';
  import MediaView from './MediaView.svelte';

  const dispatch = createEventDispatcher();
  const DEFAULT_DURATION_MS = 5000;

  let index   = 0;
  let visible = true;
  let rotateTick  = null;
  // Her geciste artan token — video onended + timeout ayni slot icin iki kez
  // ilerlemesini engeller (yaris kilidi).
  let genToken = 0;

  // asset_type metadata korunarak ayri listeler olustur.
  $: allItems  = $playlistItems.length > 0 ? $playlistItems : $campaigns;
  $: paidItems = allItems.filter(i => (i.asset_type ?? i.type) === 'creative');
  $: houseAds  = allItems.filter(i => (i.asset_type ?? i.type) === 'house_ad');
  $: mode      = paidItems.length ? 'paid' : houseAds.length ? 'house_ad' : 'fallback';
  $: activeItems = mode === 'paid' ? paidItems : houseAds;

  $: current = activeItems.length
    ? activeItems[index % activeItems.length]
    : null;

  // Liste degisince rotation'i yeniden baslat; index gecerli aralika al.
  $: activeItems, restartRotation();

  function _durationMs(item) {
    return ((item?.duration_seconds ?? 0) * 1000) || DEFAULT_DURATION_MS;
  }

  function scheduleNext(ms, token) {
    clearTimeout(rotateTick);
    rotateTick = setTimeout(() => advance(token), ms);
  }

  function advance(token) {
    if (token !== genToken) return;
    if (!activeItems.length) return;
    visible = false;
    setTimeout(() => {
      index = (index + 1) % activeItems.length;
      visible = true;
      genToken += 1;
      scheduleNext(_durationMs(activeItems[index % activeItems.length]), genToken);
    }, 400);
  }

  function restartRotation() {
    clearTimeout(rotateTick);
    if (!activeItems.length) return;
    index = Math.min(index, activeItems.length - 1);
    genToken += 1;
    scheduleNext(_durationMs(activeItems[index]), genToken);
  }

  function handleVideoEnded() {
    const tok = genToken;
    clearTimeout(rotateTick);
    advance(tok);
  }

  function handleTap() {
    clearTimeout(rotateTick);
    dispatch('start');
  }

  onDestroy(() => clearTimeout(rotateTick));
</script>

<div
  class="screen-saver"
  on:click={handleTap}
  role="button"
  tabindex="0"
  on:keydown={(e) => e.key === 'Enter' && handleTap()}
>
  <!-- Arka plan katmani -->
  <div class="ss-bg-layer" style="opacity:{visible ? 1 : 0}">
    {#if mode === 'paid' && current}
      <MediaView src={current.media_url} alt="ilan" class="ss-media"
        on:ended={handleVideoEnded} />
    {:else if mode === 'house_ad' && current}
      <img src={current.media_url} alt="icerik" class="ss-media" />
    {:else}
      <div class="ss-safe-bg"></div>
    {/if}
  </div>

  <!-- AdPromo: paid modda hic render edilmez; digerleri icin alt overlay -->
  {#if mode !== 'paid'}
    <div class="ss-adpromo-overlay">
      <AdPromo large floatCard />
    </div>
  {/if}

  <!-- Logo + CTA: her zaman en ustte -->
  <div class="ss-overlay-text">
    <Logo height="96px" light class="ss-logo-img" />
    <div class="ss-tap">
      <i class="fa-solid fa-hand-pointer ss-pulse-icon"></i>
      Baslamak icin dokunun
    </div>
  </div>
</div>

<style>
  .ss-safe-bg {
    position: absolute;
    inset: 0;
    background: radial-gradient(120% 140% at 50% 0%, #1b2436 0%, #0f1622 55%, #0b1019 100%);
  }

  .ss-adpromo-overlay {
    position: absolute;
    bottom: 40px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 20;
    max-width: min(90%, 640px);
    pointer-events: none;
  }
</style>