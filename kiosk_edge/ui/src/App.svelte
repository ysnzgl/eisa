<script>
  import { tick } from 'svelte';
  import { getRecommendations, recsToIngredientList } from './lib/ingredients.js';
  import { fetchCategories, fetchQuestions, submitSession } from './lib/api.js';
  import {
    screen,
    selectedAge, selectedSex,
    allCategories, visibleCategories,
    currentCategory, currentQuestions, currentAnswers, currentQIndex,
    catsLoading, questionsLoading,
    result,
    showCampaignOverlay,
  } from './stores/kiosk.js';

  import IdleScreen        from './components/IdleScreen.svelte';
  import DemographicsScreen from './components/DemographicsScreen.svelte';
  import WelcomeScreen     from './components/WelcomeScreen.svelte';
  import CategoryScreen    from './components/CategoryScreen.svelte';
  import SensitiveScreen   from './components/SensitiveScreen.svelte';
  import QuestionScreen    from './components/QuestionScreen.svelte';
  import ResultScreen      from './components/ResultScreen.svelte';
  import CampaignOverlay   from './components/CampaignOverlay.svelte';

  let resultScreenRef = null;

  function goTo(s) { screen.set(s); }

  function resetToIdle() {
    selectedAge.set(null);
    selectedSex.set(null);
    currentCategory.set(null);
    currentQIndex.set(0);
    currentQuestions.set([]);
    currentAnswers.set([]);
    result.set(null);
    goTo('idle');
  }

  async function loadCategories(sensitive) {
    goTo(sensitive ? 'sensitive' : 'category');
    visibleCategories.set([]);
    catsLoading.set(true);
    try {
      let cats = [];
      allCategories.update(v => { cats = v; return v; });
      if (!cats.length) {
        cats = await fetchCategories();
        allCategories.set(cats);
      }
      visibleCategories.set(cats.filter(c => c.hassas === sensitive));
    } catch (err) {
      console.error('Kategori yÃ¼kleme hatasÄ±:', err);
    } finally {
      catsLoading.set(false);
    }
  }

  async function startQuestions(cat) {
    currentCategory.set(cat);
    currentQIndex.set(0);
    currentAnswers.set([]);
    currentQuestions.set([]);
    questionsLoading.set(true);
    goTo('question');
    try {
      const qs = await fetchQuestions(cat.slug);
      currentQuestions.set(qs);
    } catch (err) {
      console.error('Soru yÃ¼kleme hatasÄ±:', err);
      currentQuestions.set([]);
    } finally {
      questionsLoading.set(false);
    }
    let qs;
    currentQuestions.update(v => { qs = v; return v; });
    if (!qs || qs.length === 0) await showFlowAResult(cat);
  }

  async function handleAnswer(answer) {
    let qs, idx, answers;
    currentQuestions.update(v => { qs = v; return v; });
    currentQIndex.update(v => { idx = v; return v; });
    currentAnswers.update(v => {
      answers = [...v, { id: qs[idx].seed_id, answer }];
      return answers;
    });
    const newIdx = idx + 1;
    currentQIndex.set(newIdx);
    if (newIdx >= qs.length) {
      let cat;
      currentCategory.update(v => { cat = v; return v; });
      await showFlowAResult(cat);
    }
  }

  async function showFlowAResult(cat) {
    let qs, answers, age, sex;
    currentQuestions.update(v => { qs = v; return v; });
    currentAnswers.update(v => { answers = v; return v; });
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });

    const recs = getRecommendations(qs, answers, age ?? '18-25', sex ?? 'M');
    const ingredientList = recsToIngredientList(recs);
    const { qrCode, qrPayload } = await doSubmitSession(false, cat?.slug ?? '', false, ingredientList);
    const firstRec = recs[0];

    result.set({
      label:       `Önerilen Etken Maddeler — ${cat?.ad ?? ''}`,
      recs,
      ana:         firstRec?.primary    ?? '—',
      destek:      firstRec?.supportive ?? '',
      isSensitive: false,
      qrCode,
      qrPayload,
    });
    goTo('result');
    await tick();
    resultScreenRef?.drawQR(qrPayload);
  }

  async function selectSensitive(cat) {
    let age, sex;
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });

    const { qrCode, qrPayload } = await doSubmitSession(true, cat?.slug ?? cat?.ad ?? '', true, []);
    result.set({
      label:       'Sessiz bildirim gönderildi',
      ana:         cat?.ad ?? cat,
      destek:      'Eczacınız sizi bekliyor — QR kodu okutunuz.',
      isSensitive: true,
      qrCode,
      qrPayload,
    });
    goTo('result');
    await tick();
    resultScreenRef?.drawQR(qrPayload);
  }

  async function doSubmitSession(isFlowB, categorySlug, isSensitiveFlow, ingredientList) {
    let age, sex, answers;
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });
    currentAnswers.update(v => { answers = v; return v; });

    try {
      return await submitSession({
        ageRange:       age,
        gender:         sex,
        categorySlug,
        isSensitiveFlow,
        answersPayload: Object.fromEntries(answers.map(a => [a.id, a.answer])),
        ingredientList,
      });
    } catch {
      const fallback = Math.random().toString(36).slice(2, 10).toUpperCase();
      return { qrCode: fallback, qrPayload: fallback };
    }
  }
</script>

<div class="kiosk">
  {#if $showCampaignOverlay}
    <CampaignOverlay on:start={() => { showCampaignOverlay.set(false); goTo('demographics'); }} />
  {:else if $screen === 'idle'}
    <IdleScreen on:start={() => goTo('demographics')} />
  {:else if $screen === 'demographics'}
    <DemographicsScreen
      on:next={() => goTo('welcome')}
      on:cancel={resetToIdle}
    />
  {:else if $screen === 'welcome'}
    <WelcomeScreen
      on:flowA={() => loadCategories(false)}
      on:flowB={() => loadCategories(true)}
    />
  {:else if $screen === 'category'}
    <CategoryScreen
      on:select={(e) => startQuestions(e.detail)}
      on:back={() => goTo('welcome')}
    />
  {:else if $screen === 'sensitive'}
    <SensitiveScreen
      on:select={(e) => selectSensitive(e.detail)}
      on:back={() => goTo('welcome')}
    />
  {:else if $screen === 'question'}
    <QuestionScreen on:answer={(e) => handleAnswer(e.detail)} />
  {:else if $screen === 'result'}
    <ResultScreen bind:this={resultScreenRef} on:done={resetToIdle} />
  {/if}
</div>
