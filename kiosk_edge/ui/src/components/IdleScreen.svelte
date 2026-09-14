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
  <!-- Logo + CTA -->
  <div class="ss-overlay-text">
    <Logo height="100px" class="ss-logo-img" />
  </div>
</div>
