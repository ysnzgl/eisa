<script>
  // Cekici (attractor) / bekleme ekrani. Uygulama acilir acilmaz dogrudan bu
  // ekran gosterilir (ayri bir "normal idle" ekrani YOKTUR).
  //   - Gercek reklam (playlist/kampanya) varsa gorseller arasinda gecis yapar.
  //   - Reklam yoksa donen "Bu Alana Reklam Verebilirsiniz" promosu gosterir.
  // Ekrana dokunulunca akis baslar.
  import { createEventDispatcher, onDestroy } from 'svelte';
  import { campaigns, playlistItems } from '../stores/kiosk.js';
  import Logo from './Logo.svelte';
  import AdPromo from './AdPromo.svelte';
  import MediaView from './MediaView.svelte';

  const dispatch = createEventDispatcher();
  const ROTATE_MS = 5000;

  let index = 0;
  let visible = true;
  let rotateTick;

  $: images = $playlistItems.length > 0
    ? $playlistItems.map(i => i.media_url).filter(Boolean)
    : $campaigns.length > 0
    ? $campaigns.map(c => c.media_url).filter(Boolean)
    : [];

  $: hasAds = images.length > 0;
  $: image = hasAds ? images[index % images.length] : null;

  // Reklam listesi degistikce gorsel donmesini (yeniden) baslat.
  $: images, restartRotation();

  function restartRotation() {
    clearInterval(rotateTick);
    if (images.length <= 1) return; // tek/sifir gorselde gecise gerek yok
    rotateTick = setInterval(() => {
      visible = false;
      setTimeout(() => {
        index = (index + 1) % images.length;
        visible = true;
      }, 600);
    }, ROTATE_MS);
  }

  function handleTap() {
    clearInterval(rotateTick);
    dispatch('start');
  }

  onDestroy(() => clearInterval(rotateTick));
</script>

<div
  class="screen-saver"
  on:click={handleTap}
  role="button"
  tabindex="0"
  on:keydown={(e) => e.key === 'Enter' && handleTap()}
>
  <div class="ss-bg-layer" style="opacity:{visible ? 1 : 0}">
    {#if hasAds}
      <MediaView src={image} alt="reklam" class="ss-media" />
    {:else}
      <!-- Reklam yok: donen "Bu Alana Reklam Verebilirsiniz" promosu -->
      <AdPromo large />
    {/if}
  </div>

  <div class="ss-overlay-text">
    <Logo height="96px" light class="ss-logo-img" />
    <div class="ss-tap">
      <i class="fa-solid fa-hand-pointer ss-pulse-icon"></i>
      Başlamak için dokunun
    </div>
  </div>
</div>

