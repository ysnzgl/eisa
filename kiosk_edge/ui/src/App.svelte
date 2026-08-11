<script>
  import { tick, onMount, onDestroy } from 'svelte';
  import { getRecommendations, recsToIngredientList } from './lib/ingredients.js';
  import { fetchCategories, fetchQuestions, fetchDanismaCategories, submitSession, fetchWifiStatus, fetchSessionSyncStatus } from './lib/api.js';
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
  import PlaylistPlayer     from './components/PlaylistPlayer.svelte';
  import WifiSetupScreen    from './components/WifiSetupScreen.svelte';

  let resultScreenRef = null;

  // ── Sahte oturum (fake session) yasam dongusu + global inaktivite ────────
  // Kategori seciminde bir id atanir; oturum QR uretildiginde (tamamlandi) veya
  // 20sn islem yapilmadiginda sonlanir. Idle/wifi disindaki HER ekranda 20sn
  // islem yoksa oturum (varsa terk edilmis olarak kapatilip) idle'a doner.
  const INACTIVITY_MS = 20_000;
  let sessionId = null;           // kategori seciminde atanan oturum id'si
  let sessionFinalized = true;    // cift gonderimi engelleyen koruma
  let sessionSubmitting = false;  // aktif HTTP gönderimi sırasında çift tetiklemeyi engeller
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
    sessionSubmitting = false;
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
      const prev = v[idx]?.answer;
      if (prev === answer) {
        // Ayni cevap — cevaplar korunur, sadece ileri git.
        answers = v;
      } else {
        // Farkli cevap — bu indeksten sonrasini temizle.
        answers = [
          ...v.slice(0, idx),
          { id: qs[idx].seed_id, questionId: qs[idx].id, answer },
        ];
      }
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

  function goBackQuestion() {
    armInactivity();
    currentQIndex.update(v => Math.max(0, v - 1));
    // Cevaplar korunur — geri donuste silme yok.
    sessionFinalized = false;
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
    const { qrCode, qrPayload, syncDurum } = await doSubmitSession(cat?.slug ?? '', false, ingredientList, completed);
    // QR olmasa bile sonuç ekranına geç; ResultScreen kendi mesajını gösterir.
    // syncDurum='hata' ise ResultScreen sarı ünlem gösterir.
    const firstRec = recs[0];
    result.set({
      label:          `Önerilen Etken Maddeler — ${cat?.ad ?? ''}`,
      recs,
      ana:            firstRec?.primary    ?? '—',
      destek:         firstRec?.supportive ?? '',
      isSensitive:    false,
      qrCode:         qrCode ?? null,
      qrPayload:      qrPayload ?? null,
      syncDurum:      syncDurum ?? 'hata',
      idempotencyKey: sessionId,
    });
    goTo('result');
    await tick();
    if (qrCode) resultScreenRef?.drawQR(qrPayload);
  }

  function startNewComplaint() {
    // Yas/cinsiyet korunur; kategori + cevap + oneri + QR temizlenir.
    currentCategory.set(null);
    currentQIndex.set(0);
    currentQuestions.set([]);
    currentAnswers.set([]);
    result.set(null);
    danismaCategories.set([]);
    sessionId = (crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`);
    sessionFinalized = false;
    sessionSubmitting = false;
    armInactivity();
    goTo('category');
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
    // sessionSubmitting guard: hızlı çift dokunmadan (rapid double-tap) korur.
    if (sessionSubmitting) return;
    sessionId = (crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`);
    sessionFinalized = false;
    sessionSubmitting = true;
    let qrCode, qrPayload, syncDurum;
    try {
      ({ qrCode, qrPayload, syncDurum } = await doSubmitConsult(cat?.slug ?? cat?.ad ?? ''));
    } finally {
      sessionSubmitting = false;
    }
    sessionFinalized = true; // Danışma hemen tamamlanır
    result.set({
      label:          'Danışma talebi gönderildi',
      ana:            cat?.ad ?? cat,
      destek:         'Eczacınız sizi bekliyor — QR kodu okutunuz.',
      isSensitive:    true,
      qrCode:         qrCode ?? null,
      qrPayload:      qrPayload ?? null,
      syncDurum:      syncDurum ?? 'hata',
      idempotencyKey: sessionId,
    });
    goTo('result');
    await tick();
    resultScreenRef?.drawQR(qrPayload);
  }

  async function doSubmitConsult(categorySlug) {
    let age, sex;
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });
    try {
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
        sessionId,
      });
    } catch (err) {
      console.error('Danisma oturumu gonderme hatasi:', err);
      return { qrCode: null, qrPayload: null, syncDurum: 'hata' };
    }
  }

  async function doSubmitSession(categorySlug, isSensitiveFlow, ingredientList, completed = true) {
    let age, sex, answers;
    selectedAge.update(v => { age = v; return v; });
    selectedSex.update(v => { sex = v; return v; });
    currentAnswers.update(v => { answers = v; return v; });

    // Abandoned sessions silently ignore errors.
    if (!completed) {
      try {
        return await submitSession({
          ageRange:       age,
          gender:         sex,
          oturumTipi:     'URUN_ONERI',
          categorySlug,
          danismaKategorisiSlug: null,
          isSensitiveFlow,
          answersPayload: Object.fromEntries(answers.map(a => [String(a.questionId ?? a.id), a.answer])),
          ingredientList,
          completed,
          sessionId,
        });
      } catch {
        return { qrCode: null }; // Abandoned sessions silently fail
      }
    }
    // For completed sessions: errors are caught; flow continues with null QR.
    try {
      return await submitSession({
        ageRange:       age,
        gender:         sex,
        oturumTipi:     'SIKAYET',
        categorySlug,
        danismaKategorisiSlug: null,
        isSensitiveFlow,
        answersPayload: Object.fromEntries(answers.map(a => [String(a.questionId ?? a.id), a.answer])),
        ingredientList,
        completed,
        sessionId,
      });
    } catch (err) {
      console.error('Oturum gonderme hatasi:', err);
      return { qrCode: null, qrPayload: null, syncDurum: 'hata' };
    }
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
        <QuestionScreen
          on:answer={(e) => handleAnswer(e.detail)}
          on:back={goBackQuestion}
        />
      {:else if $screen === 'result'}
        <ResultScreen bind:this={resultScreenRef} on:done={resetToIdle} on:newComplaint={startNewComplaint} />
      {/if}
    </div>
  {/if}

  <!-- Kalici medya oynaticisi: idle'da fullscreen, oturumda strip. Ekranlar
       arasi gecerken ayni <video> DOM instance'i KORUNUR (remount/reload yok);
       yalniz mode/CSS degisir. -->
  <div class="ad-strip-host"
       class:ad-strip-host--fullscreen={$screen === 'idle'}
       class:ad-strip-host--hidden={$screen === 'wifi_setup'}>
    {#if $screen !== 'wifi_setup'}
      <PlaylistPlayer mode={$screen === 'idle' ? 'fullscreen' : 'strip'} />
    {/if}
  </div>
</div>

<style>
</style>
