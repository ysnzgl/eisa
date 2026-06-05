<script>
  import { createEventDispatcher } from 'svelte';
  import { allCategories, visibleCategories, catsLoading } from '../stores/kiosk.js';

  const dispatch = createEventDispatcher();

  // Hiyerarsik gezinme: ust kategori -> alt kategori. `bagli_kategori_id`
  // null olanlar en ust seviyedir; cocugu olan kart bir klasor gibi acilir,
  // yaprak (cocuksuz) kart secilince anket baslar.
  let parentId = null;   // su an gosterilen seviyenin ust kategori id'si
  let stack = [];        // geri donus icin ust id yigini
  let titleStack = [];   // baslikta gosterilecek ust kategori adlari

  // allCategories yoksa (eski akis) visibleCategories'e geri dus.
  $: source = $allCategories.length ? $allCategories : $visibleCategories;

  $: levelCategories = source.filter(
    (c) => (c.bagli_kategori_id ?? null) === parentId,
  );

  function hasChildren(cat) {
    return source.some((c) => (c.bagli_kategori_id ?? null) === cat.id);
  }

  function onCardClick(cat) {
    if (hasChildren(cat)) {
      stack = [...stack, parentId];
      titleStack = [...titleStack, cat.ad];
      parentId = cat.id;
    } else {
      dispatch('select', cat);
    }
  }

  function goBack() {
    if (stack.length) {
      parentId = stack[stack.length - 1];
      stack = stack.slice(0, -1);
      titleStack = titleStack.slice(0, -1);
    } else {
      dispatch('back');
    }
  }

  $: currentTitle = titleStack.length ? titleStack[titleStack.length - 1] : null;
</script>

<div class="screen">
  <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>
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
    <div class="cat-grid">
      {#each levelCategories as cat (cat.id)}
        <button class="cat-card" on:click={() => onCardClick(cat)}>
          <i class="fa-solid {cat.ikon}"></i>
          <h3>{cat.ad}</h3>
          {#if hasChildren(cat)}
            <span class="cat-subbadge"><i class="fa-solid fa-layer-group"></i> Alt başlıklar</span>
          {/if}
        </button>
      {/each}
    </div>
  {/if}

  <div class="mt-auto pt-3">
    <button class="btn-touch btn-secondary-touch" on:click={goBack}>
      <i class="fa-solid fa-arrow-left"></i> {stack.length ? 'Üst Başlık' : 'Geri'}
    </button>
  </div>
</div>

<style>
  .cat-subbadge {
    margin-top: 6px;
    font-size: 0.8rem;
    color: #B1121B;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
</style>
