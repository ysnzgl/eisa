<script>
  // Tekrar kullanilabilir medya goruntuleyici: URL uzantisina gore <video>
  // veya <img> render eder. AdStrip ve IdleScreen (cekici ekran) tarafindan
  // ortak kullanilir.

  /** Medya URL'i (gorsel veya video). */
  export let src;
  /** Erisilebilirlik metni (gorsel icin). */
  export let alt = '';
  /** Video icin dongusel oynatim. */
  export let loop = true;
  /** Ek CSS sinifi (boyut/yerlesim icin). */
  let extraClass = '';
  export { extraClass as class };

  const VIDEO_RE = /\.(mp4|webm|ogg)$/i;
  $: isVideo = typeof src === 'string' && VIDEO_RE.test(src);
</script>

{#if isVideo}
  <!-- svelte-ignore a11y-media-has-caption -->
  <video {src} autoplay {loop} muted playsinline class={extraClass}></video>
{:else if src}
  <img {src} {alt} class={extraClass} />
{/if}
