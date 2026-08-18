<script>
  // Tekrar kullanilabilir medya goruntuleyici: URL uzantisina gore <video>
  // veya <img> render eder. AdStrip ve IdleScreen (cekici ekran) tarafindan
  // ortak kullanilir.
  import { createEventDispatcher } from 'svelte';

  /** Medya URL'i (gorsel veya video). */
  export let src;
  /** Erisilebilirlik metni (gorsel icin). */
  export let alt = '';
  /** Video icin dongusel oynatim. */
  export let loop = true;
  /** Otoriter render tipi: 'video' | 'image' | 'video/mp4' vb. (backend/api-node'dan). */
  export let type = '';
  /** Video oynatilsin mi? false → duraklat (mount/reload olmadan gizli katman icin). */
  export let playing = true;
  /** Ek CSS sinifi (boyut/yerlesim icin). */
  let extraClass = '';
  export { extraClass as class };

  const VIDEO_RE = /\.(mp4|webm|ogg)$/i;
  // Once otoriter MIME/tip; yoksa URL uzantisina geri don (guess).
  $: isVideo = type
    ? /^video/i.test(type)
    : (typeof src === 'string' && VIDEO_RE.test(src));

  const dispatch = createEventDispatcher();

  let videoEl;
  // Oynatma TAMAMEN `playing` ile yonetilir (autoplay yok → autoplay ile manuel
  // kontrol cakismaz). Gizli katman hic oynamaz; gorunur olunca reload OLMADAN
  // devam eder.
  $: if (videoEl) {
    if (playing && videoEl.paused) videoEl.play?.().catch(() => {});
    else if (!playing && !videoEl.paused) videoEl.pause?.();
  }

  function handleLoaded() {
    if (videoEl && playing && videoEl.paused) videoEl.play?.().catch(() => {});
  }

  /** Medya yükleme hatası → parent'a ilet (Faz 3: FAILED kaydı için). */
  function handleError(e) {
    dispatch('error', { src, errorEvent: e });
  }
</script>

{#if isVideo}
  <!-- svelte-ignore a11y-media-has-caption -->
  <video bind:this={videoEl} {src} {loop} muted playsinline class={extraClass}
    on:loadeddata={handleLoaded} on:error={handleError}></video>
{:else if src}
  <img {src} {alt} class={extraClass} on:error={handleError} />
{/if}
