<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { danismaCategories, danismaLoading, selectedDanismaParent } from '../stores/kiosk.js';
  import ScreenHeader from './ScreenHeader.svelte';

  const dispatch = createEventDispatcher();

  const _bySira = (a, b) => (a.sira ?? 100) - (b.sira ?? 100) || a.ad.localeCompare(b.ad, 'tr');
  $: sortedCategories = [...$danismaCategories].sort(_bySira);
  $: sortedAlt = activeParent
    ? [...(activeParent.alt_kategoriler ?? [])].sort(_bySira)
    : [];

  let activeParent = null;

  function selectParent(cat) {
    if (cat.alt_kategoriler && cat.alt_kategoriler.length > 0) {
      activeParent = cat;
      scrollEl?.scrollTo({ top: 0 });
      measureOverflow();
    } else {
      dispatch('select', cat);
    }
  }
  function selectChild(child) { dispatch('select', child); }
  function backToParents() {
    activeParent = null;
    scrollEl?.scrollTo({ top: 0 });
    measureOverflow();
  }

  // ── Overflow gostergesi ──────────────────────────────────────────────
  let scrollEl    = null;
  let hasOverflow = false;
  let isAtBottom  = false;
  let scrollRatio = 0;
  let ro = null;

  function measureOverflow() {
    if (!scrollEl) return;
    const { scrollHeight, clientHeight, scrollTop } = scrollEl;
    hasOverflow = scrollHeight > clientHeight + 2;
    const maxScroll = scrollHeight - clientHeight;
    isAtBottom  = maxScroll <= 0 || scrollTop >= maxScroll - 4;
    scrollRatio = maxScroll > 0 ? Math.min(1, scrollTop / maxScroll) : 0;
  }

  onMount(() => {
    if (!scrollEl) return;
    scrollEl.addEventListener('scroll', measureOverflow, { passive: true });
    ro = new ResizeObserver(measureOverflow);
    ro.observe(scrollEl);
    measureOverflow();
  });

  onDestroy(() => {
    scrollEl?.removeEventListener('scroll', measureOverflow);
    ro?.disconnect();
  });
</script>

<div class="screen">
  <ScreenHeader subtitle="Eczaciniza Danisin" />

  <h2 class="screen-title">Danisma konunuzu secin</h2>

  {#if $danismaLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>Yukleniyor...</span>
    </div>
  {:else if activeParent}
    <div class="scroll-wrap">
      <div class="cat-grid-scroll" bind:this={scrollEl}>
        <p class="screen-subtitle mb-3">
          <i class="fa-solid {activeParent.ikon} me-2"></i>{activeParent.ad}
        </p>
        <div class="cat-grid">
          {#each sortedAlt as child (child.id)}
            <button class="cat-card" on:click={() => selectChild(child)}>
              <i class="fa-solid {child.ikon || 'fa-circle'}"></i>
              <h3>{child.ad}</h3>
            </button>
          {/each}
        </div>
      </div>
      {#if hasOverflow && !isAtBottom}
        <div class="scroll-fade"></div>
        <div class="scroll-hint-badge">
          <i class="fa-solid fa-angles-down scroll-hint-icon"></i>
          Daha fazla seceneğ
        </div>
        <div class="scroll-pos-bar" style="height:{scrollRatio*100}%"></div>
      {/if}
    </div>
  {:else}
    {#if $danismaCategories.length === 0}
      <div class="cat-grid-scroll d-flex align-items-center justify-content-center text-center text-secondary">
        <p class="mb-0">Danisma kategorisi tanimlanmamis.</p>
      </div>
    {:else}
      <div class="scroll-wrap">
        <div class="cat-grid-scroll" bind:this={scrollEl}>
          <div class="cat-grid">
            {#each sortedCategories as cat (cat.id)}
              <button class="cat-card" on:click={() => selectParent(cat)}>
                <i class="fa-solid {cat.ikon}"></i>
                <h3>{cat.ad}</h3>
              </button>
            {/each}
          </div>
        </div>
        {#if hasOverflow && !isAtBottom}
          <div class="scroll-fade"></div>
          <div class="scroll-hint-badge">
            <i class="fa-solid fa-angles-down scroll-hint-icon"></i>
            Daha fazla seceneg
          </div>
          <div class="scroll-pos-bar" style="height:{scrollRatio*100}%"></div>
        {/if}
      </div>
    {/if}
  {/if}

  <div class="mt-auto pt-3 d-flex gap-2">
    {#if activeParent}
      <button class="btn-touch btn-primary-touch" on:click={backToParents}>
        <i class="fa-solid fa-arrow-left"></i> Geri
      </button>
    {:else}
      <button class="btn-touch btn-primary-touch" on:click={() => dispatch('back')}>
        <i class="fa-solid fa-arrow-left"></i> Geri
      </button>
    {/if}
  </div>
</div>

<style>
  .scroll-wrap {
    flex: 1; min-height: 0;
    position: relative;
    display: flex; flex-direction: column;
  }
  .cat-grid-scroll {
    flex: 1; min-height: 0;
    overflow-y: auto;
    padding-right: 6px;
    scrollbar-width: none;
  }
  .cat-grid-scroll::-webkit-scrollbar { display: none; }
  .scroll-fade {
    position: absolute; bottom: 0; left: 0; right: 0; height: 56px;
    background: linear-gradient(to bottom, transparent, rgba(249,250,251,0.95));
    pointer-events: none;
  }
  .scroll-hint-badge {
    position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
    display: flex; align-items: center; gap: 5px;
    padding: 4px 12px; border-radius: 20px;
    background: #111827cc; color: #fff; font-size: 11px; white-space: nowrap;
    pointer-events: none;
  }
  .scroll-hint-icon { animation: bounce-down 1.2s ease-in-out infinite; }
  @keyframes bounce-down {
    0%,100% { transform: translateY(0); }
    50%      { transform: translateY(3px); }
  }
  .scroll-pos-bar {
    position: absolute; top: 0; right: 0; width: 3px;
    background: #B1121B; border-radius: 2px; min-height: 16px;
    pointer-events: none; transition: height 0.15s;
  }
  .screen-subtitle { font-size: 1rem; font-weight: 600; color: var(--color-muted, #666); }
  @media (prefers-reduced-motion: reduce) {
    .scroll-hint-icon { animation: none; }
  }
</style>