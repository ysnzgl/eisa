<script>
  import { onMount, onDestroy } from 'svelte';

  // ─── Sabitler ─────────────────────────────────────────────
  const API_BASE       = 'http://127.0.0.1:8765';
  const IDLE_TIMEOUT_S = 30;

  const FALLBACK_CATEGORIES = [
    { id:1,  slug:'enerji',    name:'Enerji & Yorgunluk',       icon:'fa-battery-quarter',    is_sensitive:false,
      questions:['Sabahları yorgun mu uyanıyorsunuz?','Gün içinde enerjiniz aniden düşüyor mu?','Odaklanma güçlüğü yaşıyor musunuz?'],
      result:{ ana:'Magnezyum Sitrat', destek:'+ B12 ve B-Kompleks' } },
    { id:2,  slug:'bagisiklik',name:'Bağışıklık Sistemi',        icon:'fa-shield-halved',       is_sensitive:false,
      questions:['Sık sık soğuk algınlığı geçiriyor musunuz?','Mevsim geçişlerinde halsizlik yaşıyor musunuz?','Kalabalık ortamlarda çok zaman geçiriyor musunuz?'],
      result:{ ana:'C Vitamini (1000 mg)', destek:'+ Çinko & D3 Vitamini' } },
    { id:3,  slug:'uyku',      name:'Uyku Problemleri',          icon:'fa-moon',                is_sensitive:false,
      questions:['Gece uykuya dalmakta zorlanıyor musunuz?','Gece sık sık uyanıyor musunuz?','Sabahları dinlenmemiş mi uyanıyorsunuz?'],
      result:{ ana:'Melatonin', destek:'+ Magnezyum Bisglisinat' } },
    { id:4,  slug:'kemik',     name:'Eklem & Kas Ağrıları',      icon:'fa-bone',                is_sensitive:false,
      questions:['Merdiven çıkarken dizlerinizde ağrı oluyor mu?','Spor sonrası kas ağrıları uzun sürüyor mu?','Sabahları eklem tutukluğu yaşıyor musunuz?'],
      result:{ ana:'Tip-2 Kolajen & Glukozamin', destek:'+ Magnezyum & D3+K2' } },
    { id:5,  slug:'stres',     name:'Stres & Kaygı',             icon:'fa-brain',               is_sensitive:false,
      questions:['Sürekli gergin ya da endişeli hissediyor musunuz?','Kalp çarpıntısı ya da nefes darlığı oluyor mu?'],
      result:{ ana:'Ashwagandha', destek:'+ L-Theanine & B5' } },
    { id:6,  slug:'sindirim',  name:'Sindirim & Bağırsak',       icon:'fa-droplet',             is_sensitive:false,
      questions:['Yemek sonrası şişkinlik ya da gaz oluyor mu?','Bağırsak düzensizliği yaşıyor musunuz?'],
      result:{ ana:'Probiyotik (Multi-strain)', destek:'+ Sindirim Enzimleri' } },
    { id:7,  slug:'cinsel',    name:'Cinsel Sağlık',             icon:'fa-venus-mars',          is_sensitive:true },
    { id:8,  slug:'hemoroid',  name:'Hemoroid (Basur)',          icon:'fa-circle-exclamation',  is_sensitive:true },
    { id:9,  slug:'koku',      name:'Aşırı Ter / Vücut Kokusu', icon:'fa-spray-can',            is_sensitive:true },
    { id:10, slug:'mantar',    name:'Mantar / Egzama',           icon:'fa-hands-bubbles',       is_sensitive:true },
    { id:11, slug:'sac',       name:'Yoğun Saç Dökülmesi',      icon:'fa-user-injured',        is_sensitive:true },
    { id:12, slug:'ishal',     name:'Şiddetli İshal / Bulantı', icon:'fa-toilet',              is_sensitive:true },
  ];

  // ─── Ekran state'i ────────────────────────────────────────
  // idle | demographics | welcome | category | sensitive | question | result
  let screen = 'idle';

  // ─── Idle timer ──────────────────────────────────────────
  let idleSeconds = 0;
  let idleTick;

  function startIdleTimer() {
    idleSeconds = 0;
    clearInterval(idleTick);
    idleTick = setInterval(() => { idleSeconds++; }, 1000);
  }

  function stopIdleTimer() { clearInterval(idleTick); }

  $: idleDisplay = `${String(Math.floor(idleSeconds/60)).padStart(2,'0')}:${String(idleSeconds%60).padStart(2,'0')}`;
  $: idleOverdue  = idleSeconds >= IDLE_TIMEOUT_S;

  function goTo(s) {
    screen = s;
    if (s === 'idle') startIdleTimer(); else stopIdleTimer();
  }

  // ─── Demografik state ────────────────────────────────────
  let selectedAge = null;
  let selectedSex = null;
  $: demoReady = selectedAge && selectedSex;

  function goToDemographics() {
    selectedAge = null; selectedSex = null;
    goTo('demographics');
  }

  function resetToIdle() {
    selectedAge = null; selectedSex = null;
    currentCategory = null; currentQIndex = 0;
    result = null;
    goTo('idle');
  }

  // ─── Kategori API ────────────────────────────────────────
  let allCategories   = [];
  let catsLoading     = false;
  let offlineMode     = false;

  async function fetchCategories() {
    if (allCategories.length) return allCategories;
    catsLoading = true;
    try {
      const res = await fetch(`${API_BASE}/api/categories`, { signal: AbortSignal.timeout(4000) });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      allCategories = await res.json();
    } catch {
      offlineMode   = true;
      allCategories = FALLBACK_CATEGORIES;
    } finally {
      catsLoading = false;
    }
    return allCategories;
  }

  let visibleCategories = [];

  async function loadCategories(sensitive) {
    goTo(sensitive ? 'sensitive' : 'category');
    visibleCategories = [];
    const all = await fetchCategories();
    visibleCategories = all.filter(c => c.is_sensitive === sensitive);
  }

  // ─── Soru akışı (Akış A) ─────────────────────────────────
  let currentCategory = null;
  let currentQIndex   = 0;
  $: qProgress = currentCategory
    ? Math.round((currentQIndex / currentCategory.questions.length) * 100)
    : 0;

  async function startQuestions(categoryId) {
    let cat = allCategories.find(c => c.id === categoryId);
    if (!cat) { const all = await fetchCategories(); cat = all.find(c => c.id === categoryId); }
    if (!cat?.questions?.length) { showFlowAResult(cat); return; }
    currentCategory = cat;
    currentQIndex   = 0;
    goTo('question');
  }

  function answerQuestion() {
    currentQIndex++;
    if (currentQIndex >= currentCategory.questions.length) showFlowAResult(currentCategory);
  }

  // ─── Sonuç state'i ───────────────────────────────────────
  let result = null;       // { label, ana, destek, isSensitive, qrCode }
  let qrCanvas = null;     // QR kod canvas DOM referansı
  let answers   = {};      // Toplanan anket cevapları

  // QR canvas'a çizilir (tick sonrası DOM hazır)
  async function drawQR(code) {
    // Modülü lazy yükle — bundle boyutunu küçültür
    const QrCreator = (await import('qr-creator')).default;
    if (!qrCanvas) return;
    QrCreator.render(
      { text: code, radius: 0.5, ecLevel: 'M', fill: '#1a2e44', background: '#fff', size: 200 },
      qrCanvas,
    );
  }

  // Oturumu lokal API'ye gönderir, QR kodu alır
  async function submitSession(isFlowB, categorySlug, isSensitiveFlow, ingredientList) {
    const qrCode = await (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/session/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            age_range:           selectedAge,
            gender:              selectedSex,
            category_slug:       categorySlug,
            is_sensitive_flow:   isSensitiveFlow,
            answers_payload:     answers,
            suggested_ingredients: ingredientList,
          }),
          signal: AbortSignal.timeout(5000),
        });
        if (res.ok) {
          const data = await res.json();
          return data.qr_code;
        }
      } catch { /* Offline-First: devam et */ }
      // Fallback: kısa rastgele kod
      return Math.random().toString(36).slice(2, 10).toUpperCase();
    })();
    return qrCode;
  }

  async function showFlowAResult(cat) {
    const ingredients = cat?.result
      ? [cat.result.ana, cat.result.destek].filter(Boolean)
      : [];
    const qrCode = await submitSession(false, cat?.slug ?? '', false, ingredients);
    result = {
      label:       `Önerilen Etken Maddeler — ${cat?.name ?? ''}`,
      ana:         cat?.result?.ana    ?? '—',
      destek:      cat?.result?.destek ?? '',
      isSensitive: false,
      qrCode,
    };
    answers = {};
    goTo('result');
    // DOM hazır olduktan sonra QR çiz
    setTimeout(() => drawQR(qrCode), 50);
  }

  async function selectSensitive(cat) {
    const qrCode = await submitSession(true, cat?.slug ?? cat?.name ?? '', true, []);
    result = {
      label:       'Sessiz bildirim gönderildi',
      ana:         cat?.name ?? cat,
      destek:      'Eczacınız sizi bekliyor — QR kodu okutunuz.',
      isSensitive: true,
      qrCode,
    };
    goTo('result');
    setTimeout(() => drawQR(qrCode), 50);
  }

  // ─── Yaşam döngüsü ───────────────────────────────────────
  onMount(() => startIdleTimer());
  onDestroy(() => stopIdleTimer());
</script>

<!-- ══════════════════════════════════════════════════════════
     LAYOUT — tek konteyner, aktif ekran {#if} ile seçilir
══════════════════════════════════════════════════════════════ -->
<div class="kiosk">

  {#if offlineMode}
    <span class="offline-badge">
      <i class="fa-solid fa-wifi-slash"></i> Demo Modu
    </span>
  {/if}

  <!-- ── Akış C: IDLE / DOOH ── -->
  {#if screen === 'idle'}
    <div class="screen screen-idle" on:click={goToDemographics} role="button" tabindex="0"
         on:keydown={(e) => e.key === 'Enter' && goToDemographics()}>
      <div class="idle-bg"></div>

      <div class="idle-timer" class:overdue={idleOverdue}>
        <i class="fa-regular fa-clock"></i>
        {idleDisplay}
      </div>

      <div class="idle-content">
        <div class="idle-logo">e-<span>İSA</span></div>
        <div class="idle-tagline">Eczane İçi Sağlık Asistanınız</div>

        <!-- Reklam alanı — APScheduler'dan SQLite'a çekilen kampanya buraya gelecek -->
        <div class="idle-ad-card">
          <p class="idle-ad-label">SPONSOR REKLAM · LOKASYONA ÖZEL HEDEFLİ</p>
          <p class="idle-ad-text">
            Kış geldi, bağışıklığınızı güçlendirin!<br>
            <span style="color:#22c55e;">C Vitamini &amp; Çinko</span> kombinasyonu
          </p>
          <p class="idle-ad-note">Bu alan APScheduler tarafından SQLite'tan çekilen kampanyayı gösterir.</p>
        </div>

        <div class="idle-tap-hint">
          <i class="fa-solid fa-hand-pointer"></i> Başlamak için ekrana dokunun
        </div>
      </div>

      <div class="idle-ad-banner">
        Ekrana dokunarak sağlık danışmanınızla görüşün &nbsp;|&nbsp;
        Bu cihaz yalnızca bilgilendirme amaçlıdır, ilaç tavsiyesi değildir.
      </div>
    </div>

  <!-- ── Akış A Adım 1: Demografik Veri ── -->
  {:else if screen === 'demographics'}
    <div class="screen">
      <div class="kiosk-header">
        <div class="kiosk-logo">e-<span>İSA</span></div>
        <div class="kiosk-subtitle">Sağlık Asistanınız</div>
      </div>

      <span class="screen-badge">Adım 1 / 3 — Hızlı Profil</span>
      <h2 class="screen-title">Devam etmek için lütfen seçin</h2>

      <div class="demo-section-title">
        <i class="fa-solid fa-calendar-days text-success"></i> Yaş Aralığınız
      </div>
      <div class="demo-grid age-grid">
        {#each ['0-17','18-25','26-35','36-50','51-65','65+'] as age}
          <button class="demo-btn" class:selected={selectedAge === age}
                  on:click={() => selectedAge = age}>{age}</button>
        {/each}
      </div>

      <div class="demo-section-title" style="margin-top:20px;">
        <i class="fa-solid fa-venus-mars text-success"></i> Cinsiyetiniz
      </div>
      <div class="demo-grid sex-grid">
        <button class="demo-btn" class:selected={selectedSex === 'F'}
                on:click={() => selectedSex = 'F'}>
          <i class="fa-solid fa-venus"></i> Kadın
        </button>
        <button class="demo-btn" class:selected={selectedSex === 'M'}
                on:click={() => selectedSex = 'M'}>
          <i class="fa-solid fa-mars"></i> Erkek
        </button>
      </div>

      <div class="mt-auto d-flex flex-column gap-3">
        <button class="btn-touch btn-primary-touch" disabled={!demoReady}
                class:disabled={!demoReady} on:click={() => goTo('welcome')}>
          <i class="fa-solid fa-arrow-right"></i>
          Devam Et
        </button>
        <button class="btn-touch btn-secondary-touch" on:click={resetToIdle}>
          <i class="fa-solid fa-xmark"></i> Vazgeç
        </button>
      </div>
    </div>

  <!-- ── Akış Seçimi ── -->
  {:else if screen === 'welcome'}
    <div class="screen">
      <div class="kiosk-header">
        <div class="kiosk-logo">e-<span>İSA</span></div>
        <div class="kiosk-subtitle">Eczane İçi Sağlık Asistanınız</div>
      </div>

      <div class="flex-grow-1 d-flex flex-column justify-content-center">
        <h2 class="screen-title text-center">Nasıl Yardımcı Olabilirim?</h2>
        <div class="d-flex flex-column gap-3">
          <button class="btn-touch btn-primary-touch" on:click={() => loadCategories(false)}>
            <i class="fa-solid fa-hand-pointer"></i>
            Şikayetimi Seç &amp; Anket Çöz
            <span class="btn-sub">Takviye önerisi al, QR fiş al</span>
          </button>

          <div class="or-divider">VEYA</div>

          <button class="btn-touch btn-danger-touch" on:click={() => loadCategories(true)}>
            <i class="fa-solid fa-user-doctor"></i>
            Eczacıya Özel Danış
            <span class="btn-sub">Hassas şikayetler — sessizce ilet</span>
          </button>
        </div>
      </div>

      <div class="footer-note">
        <i class="fa-solid fa-shield-halved"></i>
        Bu sistem marka önermez. Verileriniz anonim tutulur.
      </div>
    </div>

  <!-- ── Akış A: Kategori Seçimi (DB'den) ── -->
  {:else if screen === 'category'}
    <div class="screen">
      <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>
      <span class="screen-badge">Adım 2 / 3 — Şikayet Seçimi</span>
      <h2 class="screen-title">Şikayet türünüzü seçin</h2>

      {#if catsLoading}
        <div class="loading-spinner flex-grow-1">
          <div class="spinner-ring"></div>
          <span>Kategoriler yükleniyor…</span>
        </div>
      {:else}
        <div class="cat-grid">
          {#each visibleCategories as cat (cat.id)}
            <button class="cat-card" on:click={() => startQuestions(cat.id)}>
              <i class="fa-solid {cat.icon}"></i>
              <h3>{cat.name}</h3>
            </button>
          {/each}
        </div>
      {/if}

      <div class="mt-auto pt-3">
        <button class="btn-touch btn-secondary-touch" on:click={() => goTo('welcome')}>
          <i class="fa-solid fa-arrow-left"></i> Geri
        </button>
      </div>
    </div>

  <!-- ── Akış B: Hassas Kategoriler (DB'den) ── -->
  {:else if screen === 'sensitive'}
    <div class="screen">
      <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>
      <span class="screen-badge sensitive-badge">Gizli İletişim</span>
      <h2 class="screen-title" style="color:#dc2626;">Özel Durum Bildirimi</h2>

      <div class="sensitive-info-box">
        <i class="fa-solid fa-lock-open"></i>
        <span>Seçiminiz anında <strong>eczacınızın ekranına sessizce iletilecek</strong>
          ve QR kodunuz oluşturulacak. Hiçbir soru sorulmaz.</span>
      </div>

      {#if catsLoading}
        <div class="loading-spinner flex-grow-1">
          <div class="spinner-ring"></div>
          <span>Yükleniyor…</span>
        </div>
      {:else}
        <div class="cat-grid" style="margin-top:16px;">
          {#each visibleCategories as cat (cat.id)}
            <button class="cat-card sensitive" on:click={() => selectSensitive(cat)}>
              <i class="fa-solid {cat.icon}"></i>
              <h3>{cat.name}</h3>
            </button>
          {/each}
        </div>
      {/if}

      <div class="mt-auto pt-3">
        <button class="btn-touch btn-secondary-touch" on:click={() => goTo('welcome')}>
          <i class="fa-solid fa-arrow-left"></i> Geri
        </button>
      </div>
    </div>

  <!-- ── Akış A: Soru Ekranı ── -->
  {:else if screen === 'question' && currentCategory}
    <div class="screen">
      <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>
      <span class="screen-badge">Adım 3 / 3 — Anket</span>

      <div class="q-cat-name">{currentCategory.name}</div>

      <div class="progress-bar-wrap">
        <div class="progress-bar-fill" style="width:{qProgress}%"></div>
      </div>

      <div class="question-box">
        <p class="question-text">{currentCategory.questions[currentQIndex]}</p>
        <div class="answer-row">
          <button class="btn-touch btn-primary-touch" on:click={answerQuestion}>
            <i class="fa-solid fa-check"></i> EVET
          </button>
          <button class="btn-touch btn-danger-touch" on:click={answerQuestion}>
            <i class="fa-solid fa-xmark"></i> HAYIR
          </button>
        </div>
      </div>

      <div class="q-counter">
        {currentQIndex + 1} / {currentCategory.questions.length}
      </div>
    </div>

  <!-- ── Sonuç Ekranı (Akış A & B) ── -->
  {:else if screen === 'result' && result}
    <div class="screen">
      <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>

      <div class="flex-grow-1 d-flex flex-column justify-content-center gap-3">
        <div class="result-card" class:success={!result.isSensitive} class:sensitive-result={result.isSensitive}>
          <div class="result-label">
            {#if result.isSensitive}
              <i class="fa-solid fa-lock text-danger"></i>
            {:else}
              <i class="fa-solid fa-leaf text-success"></i>
            {/if}
            {result.label}
          </div>
          <div class="result-ingredient-main" style="color:{result.isSensitive ? '#dc2626' : '#166534'}">
            {result.ana}
          </div>
          <div class="result-ingredient-sub">{result.destek}</div>
        </div>

        <div class="result-card" style="padding:24px; text-align:center;">
          <p class="qr-heading">
            <i class="fa-solid fa-ticket text-success"></i>
            Lütfen fişinizi/QR kodunuzu alınız
          </p>
          <!-- Gerçek QR kodu — qr-creator kütüphanesi ile çizilir -->
          <div class="qr-box">
            <canvas bind:this={qrCanvas} style="border-radius:8px;"></canvas>
          </div>
          {#if result.qrCode}
            <p class="qr-code-text">{result.qrCode}</p>
          {/if}
          <p class="qr-note">Bu QR kodu eczacınıza gösterin — bilgileriniz ekranına düşecek.</p>
        </div>
      </div>

      <div class="d-flex flex-column gap-2 mt-3">
        <button class="btn-touch btn-primary-touch" on:click={resetToIdle}>
          <i class="fa-solid fa-house"></i> Bitir &amp; Başa Dön
        </button>
      </div>
    </div>
  {/if}

</div>

<style>
  /* ─── Kiosk konteyner ─── */
  :global(body) {
    background: #d0d6dd;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    margin: 0;
    padding: 24px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    user-select: none;
  }

  .kiosk {
    width: 794px;
    height: 1123px;
    background: #f0f4f8;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,.25);
    overflow: hidden;
    position: relative;
  }

  /* ─── Ekranlar ─── */
  .screen {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 36px 40px 28px;
  }

  /* ─── Header ─── */
  .kiosk-header { text-align: center; margin-bottom: 24px; }
  .kiosk-logo   { font-size: 34px; font-weight: 800; color: #1a2e44; letter-spacing: -1px; }
  .kiosk-logo span { color: #22c55e; }
  .kiosk-subtitle { font-size: 15px; color: #64748b; margin-top: 2px; }

  /* ─── Dokunma butonları ─── */
  .btn-touch {
    padding: 22px 16px;
    font-size: 19px;
    font-weight: 700;
    border-radius: 16px;
    border: none;
    cursor: pointer;
    transition: transform .1s, box-shadow .1s;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    width: 100%;
  }
  .btn-touch :global(i) { font-size: 34px; }
  .btn-touch:active { transform: scale(.97); box-shadow: none !important; }
  .btn-touch.disabled { opacity: .4; cursor: not-allowed; }

  .btn-primary-touch {
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: #fff;
    box-shadow: 0 6px 24px rgba(34,197,94,.35);
  }
  .btn-danger-touch {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    color: #fff;
    box-shadow: 0 6px 24px rgba(239,68,68,.35);
  }
  .btn-secondary-touch {
    background: #e2e8f0;
    color: #475569;
    font-size: 16px;
    padding: 14px 20px;
    flex-direction: row;
    justify-content: center;
    gap: 8px;
    box-shadow: none;
  }
  .btn-sub { font-size: 13px; font-weight: 500; opacity: .8; }

  /* ─── Kategori grid ─── */
  .cat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 14px;
    flex: 1;
    align-content: start;
  }
  .cat-card {
    background: #fff;
    border: 2.5px solid #e2e8f0;
    border-radius: 16px;
    padding: 22px 12px;
    text-align: center;
    cursor: pointer;
    transition: border-color .2s, background .2s, transform .1s;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }
  .cat-card:hover  { border-color: #22c55e; background: #f0fdf4; }
  .cat-card:active { transform: scale(.97); }
  .cat-card :global(i) { font-size: 38px; color: #22c55e; }
  .cat-card.sensitive :global(i) { color: #ef4444; }
  .cat-card.sensitive:hover { border-color: #ef4444; background: #fff1f2; }
  .cat-card h3 { font-size: 15px; font-weight: 700; color: #1e293b; margin: 0; line-height: 1.3; }

  /* ─── Demografik seçim ─── */
  .demo-grid         { display: grid; gap: 12px; }
  .age-grid          { grid-template-columns: repeat(3,1fr); }
  .sex-grid          { grid-template-columns: repeat(2,1fr); }
  .demo-section-title { font-size: 19px; font-weight: 700; color: #334155; margin-bottom: 12px; }
  .demo-btn {
    background: #fff;
    border: 2.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 18px 10px;
    font-size: 17px;
    font-weight: 700;
    color: #1e293b;
    cursor: pointer;
    transition: border-color .2s, background .2s;
    text-align: center;
  }
  .demo-btn:hover  { border-color: #22c55e; background: #f0fdf4; }
  .demo-btn.selected { border-color: #22c55e; background: #dcfce7; color: #166534; }

  /* ─── Soru ekranı ─── */
  .q-cat-name   { font-size: 17px; font-weight: 700; color: #22c55e; margin-bottom: 8px; }
  .q-counter    { text-align: center; color: #94a3b8; font-size: 14px; margin-top: 16px; }
  .progress-bar-wrap {
    height: 6px;
    background: #e2e8f0;
    border-radius: 99px;
    margin-bottom: 28px;
    overflow: hidden;
  }
  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #22c55e, #16a34a);
    border-radius: 99px;
    transition: width .4s ease;
  }
  .question-box {
    background: #fff;
    border-radius: 18px;
    padding: 36px 32px;
    box-shadow: 0 4px 24px rgba(0,0,0,.08);
    text-align: center;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .question-text {
    font-size: 24px;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.4;
    margin-bottom: 36px;
  }
  .answer-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

  /* ─── Sonuç ─── */
  .result-card {
    background: #fff;
    border-radius: 18px;
    padding: 28px 24px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,.08);
  }
  .result-card.success          { border-top: 6px solid #22c55e; }
  .result-card.sensitive-result { border-top: 6px solid #ef4444; }
  .result-label           { font-size: 15px; color: #64748b; margin-bottom: 6px; }
  .result-ingredient-main { font-size: 28px; font-weight: 800; }
  .result-ingredient-sub  { font-size: 19px; color: #64748b; font-weight: 600; margin-top: 8px; }
  .qr-box {
    width: 210px; height: 210px;
    background: #fff;
    border: 4px solid #1e293b;
    border-radius: 8px;
    margin: 0 auto;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .qr-code-text {
    font-family: monospace;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #1a2e44;
    margin-top: 10px;
  }
  .qr-heading { font-size: 15px; font-weight: 700; color: #334155; margin-bottom: 16px; }
  .qr-note    { font-size: 12px; color: #94a3b8; margin-top: 12px; margin-bottom: 0; }

  /* ─── Idle ekranı (Akış C) ─── */
  .screen-idle {
    background: #0f172a;
    padding: 0;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    align-items: center;
    justify-content: center;
  }
  .idle-bg {
    position: absolute; inset: 0;
    background: linear-gradient(145deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
  }
  .idle-content {
    position: relative; z-index: 2;
    text-align: center; color: #fff; padding: 48px;
  }
  .idle-logo     { font-size: 64px; font-weight: 900; letter-spacing: -2px; }
  .idle-logo span { color: #22c55e; }
  .idle-tagline  { font-size: 22px; color: #94a3b8; margin-top: 8px; }
  .idle-ad-card  {
    margin-top: 48px;
    background: rgba(255,255,255,.07);
    border-radius: 18px;
    padding: 32px 40px;
  }
  .idle-ad-label { color: #94a3b8; font-size: 13px; margin: 0 0 6px; }
  .idle-ad-text  { color: #e2e8f0; font-size: 22px; font-weight: 700; margin: 0; }
  .idle-ad-note  { color: #64748b; font-size: 12px; margin: 12px 0 0; }
  .idle-tap-hint {
    margin-top: 56px; font-size: 18px; color: #64748b;
    animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .4; } }
  .idle-ad-banner {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: rgba(30,58,95,.8);
    backdrop-filter: blur(8px);
    padding: 18px 32px;
    text-align: center; color: #cbd5e1; font-size: 14px;
  }
  .idle-timer {
    position: absolute; top: 24px; right: 24px; z-index: 3;
    display: flex; gap: 6px; align-items: center;
    background: rgba(255,255,255,.1);
    border-radius: 99px;
    padding: 6px 14px;
    font-size: 13px; color: #94a3b8;
    transition: color .3s;
  }
  .idle-timer.overdue { color: #ef4444; }

  /* ─── Yardımcılar ─── */
  .screen-badge {
    display: inline-block;
    background: #f1f5f9; color: #64748b;
    font-size: 12px; font-weight: 600;
    border-radius: 99px;
    padding: 3px 12px;
    margin-bottom: 10px;
    text-transform: uppercase; letter-spacing: .5px;
  }
  .sensitive-badge { background: #fff1f2; color: #991b1b; }
  .screen-title    { font-size: 22px; font-weight: 800; color: #1e293b; margin-bottom: 24px; }
  .or-divider {
    display: flex; align-items: center; gap: 12px;
    color: #94a3b8; font-size: 14px; margin: 8px 0;
  }
  .or-divider::before, .or-divider::after {
    content: ''; flex: 1; height: 1px; background: #e2e8f0;
  }
  .sensitive-info-box {
    background: #fff7f7;
    border: 1.5px solid #fecaca;
    border-radius: 14px;
    padding: 14px 18px;
    color: #991b1b; font-size: 14px;
    display: flex; gap: 10px; align-items: flex-start;
    margin-bottom: 4px;
  }
  .footer-note { text-align: center; color: #94a3b8; font-size: 13px; margin-top: auto; }
  .offline-badge {
    position: absolute; top: 12px; left: 12px; z-index: 99;
    background: #fef3c7;
    border: 1px solid #fcd34d;
    border-radius: 99px;
    padding: 3px 10px;
    font-size: 11px; font-weight: 600; color: #92400e;
  }
  .loading-spinner {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 16px; color: #64748b; font-size: 16px;
  }
  .spinner-ring {
    width: 48px; height: 48px;
    border: 4px solid #e2e8f0;
    border-top-color: #22c55e;
    border-radius: 50%;
    animation: spin .8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
