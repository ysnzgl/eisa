<script>
  import { tick, onMount, onDestroy } from 'svelte';
  import { getRecommendations, recsToIngredientList } from './lib/ingredients.js';
  import { fetchCategories, fetchQuestions, fetchDanismaCategories, submitSession, fetchWifiStatus } from './lib/api.js';
  import {
    screen,
    selectedAge, selectedSex,
    allCategories, visibleCategories,
    currentCategory, currentQuestions, currentAnswers, currentQIndex,
    catsLoading, questionsLoading,
    result,
    danismaCategories, danismaLoading,
  } from './stores/kiosk.js';

  import IdleScreen         from './components/IdleScreen.svelte';
  import DemographicsScreen from './components/DemographicsScreen.svelte';
  import WelcomeScreen      from './components/WelcomeScreen.svelte';
  import CategoryScreen     from './components/CategoryScreen.svelte';
  import ConsultScreen      from './components/ConsultScreen.svelte';
  import QuestionScreen     from './components/QuestionScreen.svelte';
  import ResultScreen       from './components/ResultScreen.svelte';
  import AdStrip            from './components/AdStrip.svelte';
  import WifiSetupScreen    from './components/WifiSetupScreen.svelte';

  let resultScreenRef = null;

  // ── Sahte oturum (fake session) yasam dongusu + global inaktivite ────────
  // Kategori seciminde bir id atanir; oturum QR uretildiginde (tamamlandi) veya
  // 20sn islem yapilmadiginda sonlanir. Idle/wifi disindaki HER ekranda 20sn
  // islem yoksa oturum (varsa terk edilmis olarak kapatilip) idle'a doner.
  const INACTIVITY_MS = 20_000;
  let sessionId = null;        // kategori seciminde atanan oturum id'si
  let sessionFinalized = true; // cift gonderimi engelleyen koruma
  let inactivityTimer = null;

  function clearInactivity() {
    if (inactivityTimer) { clearTimeout(inactivityTimer); inactivityTimer = null; }
  }
  function armInactivity() {
    clearInactivity();
    inactivityTimer = setTimeout(onInactivityTimeout, INACTIVITY_MS);
  }
  async function onInactivityTimeout() {
    // 20sn islem yok → varsa terk edilmis oturumu (tamamlandi=false) kapat,
    // ardindan idle ekranina don.
    await finalizeAbandonedSession();
    resetToIdle();
  }

  // Aktif (ama tamamlanmamis) bir anket oturumu varsa terk edilmis olarak
  // sessizce gonderir — sonuc/QR ekranina YONLENDIRMEZ.
  async function finalizeAbandonedSession() {
    let cat;
    currentCategory.update(v => { cat = v; return v; });
    if (!cat || sessionFinalized) return;
    sessionFinalized = true;
    let qs, answers, age, sex;
    currentQuestions.update(v => { qs = v; return v; });
    currentAnswers.update(v => { answers = v; return v; });
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });
    const recs = getRecommendations(qs ?? [], answers ?? [], age ?? '18-25', sex ?? 'M');
    const ingredientList = recsToIngredientList(recs);
    await doSubmitSession(cat?.slug ?? '', false, ingredientList, false);
  }

  function goTo(s) { screen.set(s); }

  // Global inaktivite: idle/wifi_setup disindaki her ekranda zamanlayiciyi kur;
  // bu ekranlarda durdur. Ekran degisimi de bir aktivite sayilir (yeniden kur).
  $: currentScreenName = $screen;
  $: if (currentScreenName === 'idle' || currentScreenName === 'wifi_setup') {
    clearInactivity();
  } else {
    armInactivity();
  }

  // Herhangi bir dokunma/tus, aktif ekranda zamanlayiciyi sifirlar.
  function onUserActivity() {
    if (currentScreenName !== 'idle' && currentScreenName !== 'wifi_setup') {
      armInactivity();
    }
  }

  // Uygulama başlarken internet bağlantısı kontrol edilir.
  // Bağlantı yoksa doğrudan wifi_setup ekranı gösterilir.
  onMount(async () => {
    window.addEventListener('pointerdown', onUserActivity, { passive: true });
    window.addEventListener('keydown', onUserActivity);
    try {
      const status = await fetchWifiStatus();
      if (!status.connected) {
        goTo('wifi_setup');
      }
    } catch {
      // api-node henüz hazır değilse veya nmcli yoksa (geliştirme ortamı)
      // sessizce idle'da kal.
    }
  });

  onDestroy(() => {
    clearInactivity();
    window.removeEventListener('pointerdown', onUserActivity);
    window.removeEventListener('keydown', onUserActivity);
  });

  function resetToIdle() {
    clearInactivity();
    sessionId = null;
    sessionFinalized = true;
    selectedAge.set(null);
    selectedSex.set(null);
    currentCategory.set(null);
    currentQIndex.set(0);
    currentQuestions.set([]);
    currentAnswers.set([]);
    result.set(null);
    danismaCategories.set([]);
    goTo('idle');
  }

  async function loadCategories() {
    goTo('category');
    visibleCategories.set([]);
    catsLoading.set(true);
    try {
      let cats = [];
      allCategories.update(v => { cats = v; return v; });
      if (!cats.length) {
        cats = await fetchCategories();
        allCategories.set(cats);
      }
      visibleCategories.set(cats);
    } catch (err) {
      console.error('Kategori yükleme hatası:', err);
    } finally {
      catsLoading.set(false);
    }
  }

  async function startQuestions(cat) {
    // Kategori secimi = oturum baslangici. Yeni id ata, terk-zamanlayicisini kur.
    sessionId = (crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`);
    sessionFinalized = false;
    currentCategory.set(cat);
    currentQIndex.set(0);
    currentAnswers.set([]);
    currentQuestions.set([]);
    questionsLoading.set(true);
    goTo('question');
    armInactivity();
    try {
      const qs = await fetchQuestions(cat.slug);
      currentQuestions.set(qs);
    } catch (err) {
      console.error('Soru yükleme hatası:', err);
      currentQuestions.set([]);
    } finally {
      questionsLoading.set(false);
    }
    let qs;
    currentQuestions.update(v => { qs = v; return v; });
    if (!qs || qs.length === 0) await showFlowAResult(cat);
  }

  async function handleAnswer(answer) {
    armInactivity();
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

  async function showFlowAResult(cat, completed = true) {
    // Cift sonlandirmayi engelle (zaman asimi + normal bitis yarisabilir).
    if (sessionFinalized) return;
    sessionFinalized = true;
    clearInactivity();
    let qs, answers, age, sex;
    currentQuestions.update(v => { qs = v; return v; });
    currentAnswers.update(v => { answers = v; return v; });
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });

    const recs = getRecommendations(qs, answers, age ?? '18-25', sex ?? 'M');
    const ingredientList = recsToIngredientList(recs);
    const { qrCode, qrPayload } = await doSubmitSession(cat?.slug ?? '', false, ingredientList, completed);
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

  async function loadDanismaCategories() {
    goTo('consult');
    danismaCategories.set([]);
    danismaLoading.set(true);
    try {
      const cats = await fetchDanismaCategories();
      danismaCategories.set(cats ?? []);
    } catch (err) {
      console.error('Danışma kategori yükleme hatası:', err);
    } finally {
      danismaLoading.set(false);
    }
  }

  async function selectConsult(cat) {
    // Danışma kategorisi seçimi = oturum başlangıcı. Yeni id ata.
    sessionId = (crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`);    sessionFinalized = false;
    const { qrCode, qrPayload } = await doSubmitConsult(cat?.slug ?? cat?.ad ?? '');
    sessionFinalized = true; // Danışma hemen tamamlanır
    result.set({
      label:       'Danışma talebi gönderildi',
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

  async function doSubmitConsult(categorySlug) {
    let age, sex;
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });
    // No try/catch: backend QR is authoritative. Caller handles error.
    return await submitSession({
      ageRange:       age,
      gender:         sex,
      oturumTipi:     'OZEL_DANISMANLIK',
      categorySlug:   null,
      danismaKategorisiSlug: categorySlug,
      isSensitiveFlow: true,
      answersPayload:  {},
      ingredientList:  [],
      completed:       true,
    });
  }

  async function doSubmitSession(categorySlug, isSensitiveFlow, ingredientList, completed = true) {
    let age, sex, answers;
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });
    currentAnswers.update(v => { answers = v; return v; });

    // No try/catch for completed sessions: backend QR is authoritative.
    // For abandoned sessions, errors are silently ignored.
    if (!completed) {
      try {
        return await submitSession({
          ageRange:       age,
          gender:         sex,
          oturumTipi:     'URUN_ONERI',
          categorySlug,
          danismaKategorisiSlug: null,
          isSensitiveFlow,
          answersPayload: Object.fromEntries(answers.map(a => [a.id, a.answer])),
          ingredientList,
          completed,
        });
      } catch {
        return { qrCode: null }; // Abandoned sessions silently fail
      }
    }
    return await submitSession({
      ageRange:       age,
      gender:         sex,
      oturumTipi:     'SIKAYET',
      categorySlug,
      danismaKategorisiSlug: null,
      isSensitiveFlow,
      answersPayload: Object.fromEntries(answers.map(a => [a.id, a.answer])),
      ingredientList,
      completed,
    });
  }
</script>

<div class="kiosk">
  {#if $screen === 'wifi_setup'}
    <!-- WiFi Kurulum: internet yoksa ilk ekran -->
    <WifiSetupScreen on:connected={() => goTo('idle')} />
  {:else if $screen === 'idle'}
    <!-- Idle / Screensaver: tam ekran -->
    <IdleScreen on:start={() => goTo('demographics')} />
  {:else}
    <!-- Anket bölgesi: 3/4 üst -->
    <div class="kiosk-main">
      {#if $screen === 'demographics'}
        <DemographicsScreen
          on:next={() => goTo('welcome')}
          on:cancel={resetToIdle}
        />
      {:else if $screen === 'welcome'}
        <WelcomeScreen
          on:flowA={loadCategories}
          on:flowConsult={loadDanismaCategories}
        />
      {:else if $screen === 'category'}
        <CategoryScreen
          on:select={(e) => startQuestions(e.detail)}
          on:back={() => goTo('welcome')}
        />
      {:else if $screen === 'consult'}
        <ConsultScreen
          on:select={(e) => selectConsult(e.detail)}
          on:back={() => goTo('welcome')}
        />
      {:else if $screen === 'question'}
        <QuestionScreen on:answer={(e) => handleAnswer(e.detail)} />
      {:else if $screen === 'result'}
        <ResultScreen bind:this={resultScreenRef} on:done={resetToIdle} />
      {/if}
    </div>
  {/if}

  <!-- Reklam bandı: her zaman mount, idle ve wifi_setup ekranlarında gizli -->
  <div class="ad-strip-host" class:ad-strip-host--hidden={$screen === 'idle' || $screen === 'wifi_setup'}>
    <AdStrip />
  </div>
</div>
