<script>
  import { createEventDispatcher } from 'svelte';
  import { currentCategory, currentQuestions, currentQIndex, questionsLoading, currentAnswers } from '../stores/kiosk.js';
  import ScreenHeader from './ScreenHeader.svelte';
  import { t, localize } from '../lib/i18n.js';

  const dispatch = createEventDispatcher();

  $: qProgress = $currentQuestions.length
    ? Math.round(($currentQIndex / $currentQuestions.length) * 100)
    : 0;

  $: currentAnswer = $currentAnswers[$currentQIndex]?.answer ?? null;
</script>

<div class="screen">
  <ScreenHeader />
  <span class="screen-badge">{$t('question.step')}</span>

  <div class="q-cat-name">{$localize($currentCategory)}</div>

  <div class="progress-bar-wrap">
    <div class="progress-bar-fill" style="width:{qProgress}%"></div>
  </div>

  {#if $questionsLoading}
    <div class="loading-spinner flex-grow-1">
      <div class="spinner-ring"></div>
      <span>{$t('question.loading')}</span>
    </div>
  {:else if $currentQuestions[$currentQIndex]}
    <div class="question-box">
      <p class="question-text">{$localize($currentQuestions[$currentQIndex], 'metin')}</p>
      <div class="answer-row">
        <button
          class="btn-touch btn-primary-touch btn-evet"
          class:btn-answer-selected={currentAnswer === 'Y'}
          on:click={() => dispatch('answer', 'Y')}
        >
          <i class="fa-solid fa-check"></i> {$t('common.yes')}
        </button>
        <button
          class="btn-touch btn-danger-touch btn-hayir"
          class:btn-answer-selected={currentAnswer === 'N'}
          on:click={() => dispatch('answer', 'N')}
        >
          <i class="fa-solid fa-xmark"></i> {$t('common.no')}
        </button>
      </div>
    </div>

    <div class="q-counter">
      {$currentQIndex + 1} / {$currentQuestions.length}
    </div>
  {/if}

  {#if $currentQIndex > 0}
    <div class="mt-auto pt-2">
      <button class="btn-touch btn-primary-touch" on:click={() => dispatch('back')}>
        <i class="fa-solid fa-arrow-left"></i> {$t('question.prev')}
      </button>
    </div>
  {/if}
</div>
