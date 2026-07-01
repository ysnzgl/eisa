<script>
  // Tekrar kullanilabilir e-İSA logo bileseni.
  // Tum kioskta "e-İSA" yazisinin yerine resmi marka logosu (SVG) gosterilir.
  // Koyu zeminlerde okunabilirlik icin beyaz (light) varyant kullanilir.
  import logoDark from '../assets/eisa-logo.svg';
  import logoLight from '../assets/eisa-logo-light.svg';

  /** Logonun yuksekligi (CSS birimi ile, orn. "40px"). */
  export let height = '40px';
  /** Koyu zemin uzerinde beyaz logo varyanti. */
  export let light = false;
  /** Ek CSS sinifi (opsiyonel). */
  let extraClass = '';
  export { extraClass as class };

  $: src = light ? logoLight : logoDark;
</script>

<img
  {src}
  alt="e-İSA — Eczane İçi Sağlık Asistanınız"
  class="eisa-logo {extraClass}"
  style="height:{height}"
/>

<style>
  .eisa-logo {
    width: auto;
    display: block;
    object-fit: contain;
    user-select: none;
    -webkit-user-drag: none;
  }
</style>
