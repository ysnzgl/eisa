<script>
  import { createEventDispatcher } from 'svelte';
  import { currentCategory, currentQuestions, currentQIndex, questionsLoading } from '../stores/kiosk.js';

  const dispatch = createEventDispatcher();

  $: qProgress = $currentQuestions.length
    ? Math.round(($currentQIndex / $currentQuestions.length) * 100)
    : 0;
</script>

<div class="screen">
  <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>
  <span class="screen-badge">Adım 3 / 3 — Anket</span>

  <div class="q-cat-name">{$currentCategory?.name ?? ''}</div>

  <div class="progress-bar-wrap">
    <div class="progress-bar-fill" style="width:{qProgress}%"></div>
  </div>

  {#if $questionsLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>Sorular yükleniyor…</span>
    </div>
  {:else if $currentQuestions[$currentQIndex]}
    <div class="question-box">
      <p class="question-text">{$currentQuestions[$currentQIndex].text}</p>
      <div class="answer-row">
        <button class="btn-touch btn-primary-touch" on:click={() => dispatch('answer', 'Y')}>
          <i class="fa-solid fa-check"></i> EVET
        </button>
        <button class="btn-touch btn-danger-touch" on:click={() => dispatch('answer', 'N')}>
          <i class="fa-solid fa-xmark"></i> HAYIR
        </button>
      </div>
    </div>

    <div class="q-counter">
      {$currentQIndex + 1} / {$currentQuestions.length}
    </div>
  {/if}
</div>
