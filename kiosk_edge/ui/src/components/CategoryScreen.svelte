<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { allCategories, visibleCategories, catsLoading } from '../stores/kiosk.js';
  import ScreenHeader from './ScreenHeader.svelte';

  const dispatch = createEventDispatcher();

  let parentId = null;
  let stack = [];
  let titleStack = [];

  $: source = $allCategories.length ? $allCategories : $visibleCategories;
  $: levelCategories = source.filter((c) => (c.bagli_kategori_id ?? null) === parentId);

  function hasChildren(cat) {
    return source.some((c) => (c.bagli_kategori_id ?? null) === cat.id);
  }

  function onCardClick(cat) {
    if (hasChildren(cat)) {
      stack = [...stack, parentId];
      titleStack = [...titleStack, cat.ad];
      parentId = cat.id;
      scrollEl?.scrollTo({ top: 0 });
      measureOverflow();
    } else {
      dispatch('select', cat);
    }
  }

  function goBack() {
    if (stack.length) {
      parentId = stack[stack.length - 1];
      stack = stack.slice(0, -1);
      titleStack = titleStack.slice(0, -1);
      scrollEl?.scrollTo({ top: 0 });
      measureOverflow();
    } else {
      dispatch('back');
    }
  }

  $: currentTitle = titleStack.length ? titleStack[titleStack.length - 1] : null;

  // ── Overflow göstergesi ──────────────────────────────────────────────
  let scrollEl = null;
  let hasOverflow = false;
  let isAtBottom  = false;
  let scrollRatio = 0;
  let hintOnce    = false;
  let ro = null;

  function measureOverflow() {
    if (!scrollEl) return;
    const { scrollHeight, clientHeight, scrollTop } = scrollEl;
    hasOverflow = scrollHeight > clientHeight + 2;
    const maxScroll = scrollHeight - clientHeight;
    isAtBottom  = maxScroll <= 0 || scrollTop >= maxScroll - 4;
    scrollRatio = maxScroll > 0 ? Math.min(1, scrollTop / maxScroll) : 0;
  }

  function onScroll() { measureOverflow(); }

  onMount(() => {
    if (!scrollEl) return;
    scrollEl.addEventListener('scroll', onScroll, { passive: true });
    ro = new ResizeObserver(measureOverflow);
    ro.observe(scrollEl);
    measureOverflow();
    // Bir kez hafif scroll hint animasyonu
    if (!hintOnce && hasOverflow) {
      hintOnce = true;
      setTimeout(() => {
        scrollEl?.scrollTo({ top: 22, behavior: 'smooth' });
        setTimeout(() => scrollEl?.scrollTo({ top: 0, behavior: 'smooth' }), 380);
      }, 600);
    }
  });

  onDestroy(() => {
    scrollEl?.removeEventListener('scroll', onScroll);
    ro?.disconnect();
  });
</script>

<div class="screen">
  <ScreenHeader />
  <span class="screen-badge">Adım 2 / 3 — Şikayet Seçimi</span>
  <h2 class="screen-title">
    {#if currentTitle}{currentTitle} — alt başlık seçin{:else}Şikayet türünüzü seçin{/if}
  </h2>

  {#if $catsLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>Kategoriler yükleniyor…</span>
    </div>
  {:else if levelCategories.length === 0}
    <div class="loading-spinner flex-grow-1">
      <span>Bu başlık altında kategori bulunamadı.</span>
    </div>
  {:else}
    <div class="scroll-wrap">
      <div class="cat-grid-scroll" bind:this={scrollEl}>
        <div class="cat-grid">
          {#each levelCategories as cat (cat.id)}
            <button class="cat-card" on:click={() => onCardClick(cat)}>
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
          Daha fazla seçenek
        </div>
        <div class="scroll-pos-bar" style="height:{scrollRatio*100}%"></div>
      {/if}
    </div>
  {/if}

  <div class="mt-auto pt-3">
    <button class="btn-touch btn-primary-touch" on:click={goBack}>
      <i class="fa-solid fa-arrow-left"></i>Geri
    </button>
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
  @media (prefers-reduced-motion: reduce) {
    .scroll-hint-icon { animation: none; }
  }
</style>
