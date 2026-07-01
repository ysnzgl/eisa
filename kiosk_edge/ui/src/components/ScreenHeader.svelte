<script>
  // Tekrar kullanilabilir ekran basligi: marka logosu + opsiyonel alt baslik.
  // Tum anket/danisma ekranlarinda ortak kullanilir.
  import Logo from './Logo.svelte';

  /** Logo yuksekligi (CSS birimi). */
  export let height = '46px';
  /** Opsiyonel alt baslik metni. */
  export let subtitle = '';
</script>

<div class="kiosk-header">
  <Logo {height} class="kiosk-logo-img" />
  {#if subtitle}<div class="kiosk-subtitle">{subtitle}</div>{/if}
</div>
