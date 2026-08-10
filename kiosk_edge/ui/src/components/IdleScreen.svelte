<script>
  // Idle CTA overlay. Medya artik kalici PlaylistPlayer'da (arkada, z-index:100);
  // bu katman seffaftir ve yalniz logo + "Baslamak icin dokunun" + dokunma
  // hedefi saglar. Burada video YOKTUR → idle<->oturum gecisinde kalici
  // oynaticidaki <video> DOM instance'i korunur.
  import { createEventDispatcher } from 'svelte';
  import Logo from './Logo.svelte';

  const dispatch = createEventDispatcher();

  function handleTap() {
    dispatch('start');
  }
</script>

<div
  class="screen-saver"
  on:click={handleTap}
  role="button"
  tabindex="0"
  on:keydown={(e) => e.key === 'Enter' && handleTap()}
>
  <!-- Metin okunurlugu icin hafif ust/alt scrim (arkadaki video uzerinde). -->
  <div class="ss-scrim" aria-hidden="true"></div>

  <!-- Logo + CTA -->
  <div class="ss-overlay-text">
    <Logo height="96px" light class="ss-logo-img" />
    <div class="ss-tap">
      <i class="fa-solid fa-hand-pointer ss-pulse-icon"></i>
      Baslamak icin dokunun
    </div>
  </div>
</div>

<style>
  .ss-scrim {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      to bottom,
      rgba(0, 0, 0, 0.38) 0%,
      rgba(0, 0, 0, 0) 26%,
      rgba(0, 0, 0, 0) 72%,
      rgba(0, 0, 0, 0.38) 100%
    );
    pointer-events: none;
  }
</style>