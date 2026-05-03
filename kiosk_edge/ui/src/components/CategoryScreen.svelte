<script>
  import { createEventDispatcher } from 'svelte';
  import { visibleCategories, catsLoading } from '../stores/kiosk.js';

  const dispatch = createEventDispatcher();
</script>

<div class="screen">
  <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>
  <span class="screen-badge">Adım 2 / 3 — Şikayet Seçimi</span>
  <h2 class="screen-title">Şikayet türünüzü seçin</h2>

  {#if $catsLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>Kategoriler yükleniyor…</span>
    </div>
  {:else}
    <div class="cat-grid">
      {#each $visibleCategories as cat (cat.id)}
        <button class="cat-card" on:click={() => dispatch('select', cat)}>
          <i class="fa-solid {cat.ikon}"></i>
          <h3>{cat.ad}</h3>
        </button>
      {/each}
    </div>
  {/if}

  <div class="mt-auto pt-3">
    <button class="btn-touch btn-secondary-touch" on:click={() => dispatch('back')}>
      <i class="fa-solid fa-arrow-left"></i> Geri
    </button>
  </div>
</div>
