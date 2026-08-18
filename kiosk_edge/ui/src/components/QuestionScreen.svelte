<script>
  import { createEventDispatcher } from 'svelte';
  import { currentCategory, currentQuestions, currentQIndex, questionsLoading, currentAnswers } from '../stores/kiosk.js';
  import ScreenHeader from './ScreenHeader.svelte';

  const dispatch = createEventDispatcher();

  $: qProgress = $currentQuestions.length
    ? Math.round(($currentQIndex / $currentQuestions.length) * 100)
    : 0;

  $: currentAnswer = $currentAnswers[$currentQIndex]?.answer ?? null;
</script>

<div class="screen">
  <ScreenHeader />
  <span class="screen-badge">Adim 3 / 3</span>

  <div class="q-cat-name">{$currentCategory?.ad ?? ''}</div>

  <div class="progress-bar-wrap">
    <div class="progress-bar-fill" style="width:{qProgress}%"></div>
  </div>

  {#if $questionsLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>Sorular yukleniyor...</span>
    </div>
  {:else if $currentQuestions[$currentQIndex]}
    <div class="question-box">
      <p class="question-text">{$currentQuestions[$currentQIndex].metin}</p>
      <div class="answer-row">
        <button
          class="btn-touch btn-primary-touch"
          class:btn-answer-selected={currentAnswer === 'Y'}
          on:click={() => dispatch('answer', 'Y')}
        >
          <i class="fa-solid fa-check"></i> EVET
        </button>
        <button
          class="btn-touch btn-danger-touch btn-hayir"
          class:btn-answer-selected={currentAnswer === 'N'}
          on:click={() => dispatch('answer', 'N')}
        >
          <i class="fa-solid fa-xmark"></i> HAYIR
        </button>
      </div>
    </div>

    <div class="q-counter">
      {$currentQIndex + 1} / {$currentQuestions.length}
    </div>
  {/if}

  {#if $currentQIndex > 0}
    <div class="mt-auto pt-2">
      <button class="btn-touch btn-secondary-touch" on:click={() => dispatch('back')}>
        <i class="fa-solid fa-arrow-left"></i> Onceki Soru
      </button>
    </div>
  {/if}
</div>

<style>
  .btn-answer-selected {
    outline: 3px solid #B1121B;
    outline-offset: 2px;
  }
  /* HAYIR butonu için koyu gri ton */
  .btn-hayir {
    background: linear-gradient(135deg, #4B5563, #374151);
    box-shadow: 0 6px 24px rgba(55, 65, 81, 0.35);
  }
</style>