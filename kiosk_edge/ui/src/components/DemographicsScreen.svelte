<script>
  import { createEventDispatcher } from 'svelte';
  import { selectedAge, selectedSex } from '../stores/kiosk.js';

  const dispatch = createEventDispatcher();

  $: demoReady = $selectedAge && $selectedSex;

  function proceed() {
    if (demoReady) dispatch('next');
  }
</script>

<div class="screen">
  <div class="kiosk-header">
    <div class="kiosk-logo">e-<span>İSA</span></div>
    <div class="kiosk-subtitle">Sağlık Asistanınız</div>
  </div>

  <span class="screen-badge">Adım 1 / 3 — Hızlı Profil</span>
  <h2 class="screen-title">Devam etmek için lütfen seçin</h2>

  <div class="demo-section-title">
    <i class="fa-solid fa-calendar-days text-success"></i> Yaş Aralığınız
  </div>
  <div class="demo-grid age-grid">
    {#each ['0-17', '18-25', '26-35', '36-50', '51-65', '65+'] as age}
      <button
        class="demo-btn"
        class:selected={$selectedAge === age}
        on:click={() => selectedAge.set(age)}
      >{age}</button>
    {/each}
  </div>

  <div class="demo-section-title" style="margin-top:20px;">
    <i class="fa-solid fa-venus-mars text-success"></i> Cinsiyetiniz
  </div>
  <div class="demo-grid sex-grid">
    <button
      class="demo-btn"
      class:selected={$selectedSex === 'F'}
      on:click={() => selectedSex.set('F')}
    >
      <i class="fa-solid fa-venus"></i> Kadın
    </button>
    <button
      class="demo-btn"
      class:selected={$selectedSex === 'M'}
      on:click={() => selectedSex.set('M')}
    >
      <i class="fa-solid fa-mars"></i> Erkek
    </button>
  </div>

  <div class="mt-auto d-flex flex-column gap-2">
    <button
      class="btn-touch btn-primary-touch"
      disabled={!demoReady}
      class:disabled={!demoReady}
      on:click={proceed}
    >
      <i class="fa-solid fa-arrow-right"></i>
      Devam Et
    </button>
    <button class="btn-touch btn-secondary-touch" on:click={() => dispatch('cancel')}>
      <i class="fa-solid fa-xmark"></i> Vazgeç
    </button>
  </div>
</div>
