<script>
  import { createEventDispatcher } from 'svelte';
  import { danismaCategories, danismaLoading, selectedDanismaParent } from '../stores/kiosk.js';

  const dispatch = createEventDispatcher();

  /** Seçili üst kategori (alt kategorileri göstermek için). */
  let activeParent = null;

  function selectParent(cat) {
    if (cat.alt_kategoriler && cat.alt_kategoriler.length > 0) {
      activeParent = cat;
    } else {
      dispatch('select', cat);
    }
  }

  function selectChild(child) {
    dispatch('select', child);
  }

  function backToParents() {
    activeParent = null;
  }
</script>

<div class="screen">
  <div class="kiosk-header">
    <div class="kiosk-logo">e-<span>İSA</span></div>
    <div class="kiosk-subtitle">Eczacınıza Danışın</div>
  </div>

  <h2 class="screen-title">Danışma konunuzu seçin</h2>

  {#if $danismaLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>Yükleniyor…</span>
    </div>
  {:else if activeParent}
    <!-- Alt kategoriler görünümü -->
    <p class="screen-subtitle mb-3">
      <i class="fa-solid {activeParent.ikon} me-2"></i>{activeParent.ad}
    </p>
    <div class="cat-grid">
      {#each activeParent.alt_kategoriler as child (child.id)}
        <button class="cat-card" on:click={() => selectChild(child)}>
          <i class="fa-solid {child.ikon || 'fa-circle'}"></i>
          <h3>{child.ad}</h3>
        </button>
      {/each}
    </div>
  {:else}
    <!-- Üst kategoriler -->
    {#if $danismaCategories.length === 0}
      <div class="flex-grow-1 d-flex align-items-center justify-content-center text-center text-secondary">
        <p>Danışma kategorisi tanımlanmamış.</p>
      </div>
    {:else}
      <div class="cat-grid">
        {#each $danismaCategories as cat (cat.id)}
          <button class="cat-card" on:click={() => selectParent(cat)}>
            <i class="fa-solid {cat.ikon}"></i>
            <h3>{cat.ad}</h3>
            {#if cat.alt_kategoriler && cat.alt_kategoriler.length > 0}
              <span class="cat-sub-count">{cat.alt_kategoriler.length} alt konu</span>
            {/if}
          </button>
        {/each}
      </div>
    {/if}
  {/if}

  <div class="mt-auto pt-3 d-flex gap-2">
    {#if activeParent}
      <button class="btn-touch btn-secondary-touch" on:click={backToParents}>
        <i class="fa-solid fa-arrow-left"></i> Geri
      </button>
    {:else}
      <button class="btn-touch btn-secondary-touch" on:click={() => dispatch('back')}>
        <i class="fa-solid fa-arrow-left"></i> Geri
      </button>
    {/if}
  </div>
</div>

<style>
  .cat-sub-count {
    font-size: 0.65rem;
    opacity: 0.7;
    margin-top: 0.2rem;
  }
  .screen-subtitle {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-muted, #666);
  }
</style>
