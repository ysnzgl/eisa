<script>
  import { createEventDispatcher } from 'svelte';
  import { visibleCategories, catsLoading } from '../stores/kiosk.js';

  const dispatch = createEventDispatcher();
</script>

<div class="screen">
  <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>
  <span class="screen-badge sensitive-badge">Gizli İletişim</span>
  <h2 class="screen-title" style="color:#dc2626;">Özel Durum Bildirimi</h2>

  <div class="sensitive-info-box">
    <i class="fa-solid fa-lock-open"></i>
    <span>Seçiminiz anında <strong>eczacınızın ekranına sessizce iletilecek</strong>
      ve QR kodunuz oluşturulacak. Hiçbir soru sorulmaz.</span>
  </div>

  {#if $catsLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>Yükleniyor…</span>
    </div>
  {:else}
    <div class="cat-grid" style="margin-top:16px;">
      {#each $visibleCategories as cat (cat.id)}
        <button class="cat-card sensitive" on:click={() => dispatch('select', cat)}>
          <i class="fa-solid {cat.icon}"></i>
          <h3>{cat.name}</h3>
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
