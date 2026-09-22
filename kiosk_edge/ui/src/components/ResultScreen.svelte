<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { result } from '../stores/kiosk.js';
  import Logo from './Logo.svelte';
  import { fetchSessionSyncStatus } from '../lib/api.js';

  const dispatch = createEventDispatcher();

  let qrCanvas = null;
  let syncDurum = null;
  let pollTimer = null;
  let showOtherIngredients = false;

  async function pollSync() {
    const key = $result?.idempotencyKey;
    if (!key) return;
    try {
      const status = await fetchSessionSyncStatus(key);
      if (status?.sync_durum === 'gonderildi') syncDurum = 'gonderildi';
    } catch { /* ignore */ }
  }

  onMount(() => {
    syncDurum = $result?.syncDurum ?? null;
    if (syncDurum === 'bekliyor') {
      pollTimer = setTimeout(async () => {
        await pollSync();
        if (syncDurum === 'bekliyor') {
          pollTimer = setTimeout(pollSync, 8000);
        }
      }, 3000);
    }
  });

  onDestroy(() => { if (pollTimer) clearTimeout(pollTimer); });

  export async function drawQR(code) {
    if (!code) return;
    const QrCreator = (await import('qr-creator')).default;
    if (!qrCanvas) return;
    // Şifrelenmiş payload uzun olabileceği için Q yerine L, modül daha sık.
    QrCreator.render(
      { text: code, radius: 0.4, ecLevel: 'L', fill: '#111827', background: '#fff', size: 180 },
      qrCanvas,
    );
  }
</script>

<div class="screen">
  <div class="result-header">
    <Logo height="100px" />
    {#if syncDurum === 'bekliyor' || syncDurum === 'hata'}
      <span class="sync-warn" title="Sunucuya henüz gönderilemedi">
        <i class="fa-solid fa-triangle-exclamation"></i>
      </span>
    {/if}
  </div>

  <div class="flex-grow-1 d-flex flex-column justify-content-center gap-2">
    <div
      class="result-card"
      class:success={!$result?.isSensitive}
      class:sensitive-result={$result?.isSensitive}
    >
      <div class="result-label">
        {#if $result?.isSensitive}
          <i class="fa-solid fa-lock text-danger"></i>
        {:else}
          <i class="fa-solid fa-leaf text-success"></i>
        {/if}
        {$result?.label ?? ''}
      </div>
      {#if $result?.recs?.length}
        {@const firstRec = $result.recs[0]}
        <div class="ingredient-area">
          <div class="ingredient-box">
            {firstRec.primary}{#if firstRec.supportive} + {firstRec.supportive}{/if}
          </div>
        </div>
        {#if $result?.recs?.length > 1}
          <div class="ingredient-note">
            <div class="ingredient-note-title">
              <i class="fa-solid fa-info-circle"></i>
              Bir seçenek ekranda, diğerleri eczacınızda!
            </div>
            <button 
              class="ingredient-btn"
              on:click={() => showOtherIngredients = !showOtherIngredients}
            >
              <i class="fa-solid fa-{showOtherIngredients ? 'chevron-up' : 'chevron-down'}"></i>
              Diğer etken maddeler için tıklayınız
            </button>
            {#if showOtherIngredients && $result?.recs?.length > 1}
              <div class="other-ingredients">
                {#each $result.recs.slice(1) as rec (rec.primary)}
                  <div class="ingredient-item">
                    <span class="ingredient-icon">→</span>
                    {rec.primary}{#if rec.supportive} + {rec.supportive}{/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      {/if}
    </div>

    <div class="result-card" style="text-align:center;">
      <p class="qr-heading">
        <i class="fa-solid fa-ticket text-success"></i>
        Lütfen Fişinizi/QR kodunuzu Eczacınıza gösterin. <br />
      </p>
      {#if $result?.qrCode}
        <div class="qr-box">
          <canvas bind:this={qrCanvas} style="border-radius:8px;"></canvas>
        </div>
        <p class="qr-code-text">{$result.qrCode}</p>
      {:else}
        <p style="color:#6B7280; font-size:14px; margin:12px 0;">QR kodu oluşturulamadı. Lütfen eczacıya danışın.</p>
      {/if}
      <p class="qr-note">Öneriler için profesyonellere danışın. Yapay zeka tarafından üretilmiş yanıtlarda hata olabilir.</p>
    </div>

    {#if $result?.devPreview}
      <div class="receipt-preview">
        <p class="receipt-preview-label">
          <i class="fa-solid fa-print"></i> Termal fiş önizlemesi
        </p>
        <div class="receipt-paper">
          {#if $result?.baskiLogoUrl}
            <img src={$result.baskiLogoUrl} alt="Barkod logosu" class="receipt-logo" />
          {:else}
            <p class="receipt-eisa">e-ISA</p>
          {/if}
          <p class="receipt-text">Sağlıklı günler diler</p>
          <p class="receipt-text" style="font-size:11px; color:#9ca3af;">— QR kodu yazıcıdan çıkar —</p>
          <p class="receipt-text" style="font-size:11px; margin-top:2px;">{$result.qrCode}</p>
        </div>
      </div>
    {/if}
  </div>

  <div class="d-flex flex-column gap-2 mt-3">
    <button class="btn-touch btn-secondary-touch" on:click={() => dispatch('newComplaint')}>
      <i class="fa-solid fa-rotate-left"></i> Başka Bir Şikayet Seç
    </button>
    <button class="btn-touch btn-primary-touch" on:click={() => dispatch('done')}>
      <i class="fa-solid fa-house"></i> Ana Sayfaya Dön
    </button>
  </div>
</div>

<style>
  .result-header {
    position: relative;
    text-align: center;
    margin-bottom: 24px;
  }
  .result-header :global(.eisa-logo) {
    margin: 0 auto;
  }
  .sync-warn {
    position: absolute;
    top: 50%;
    right: 0;
    transform: translateY(-50%);
    font-size: 22px;
    color: #d97706;
    line-height: 1;
    pointer-events: none;
  }
  .ingredient-area {
    background: #7f1d1d;
    border-radius: 12px;
    padding: 14px;
    margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
  }
  .ingredient-box {
    background: #fff;
    border-radius: 10px;
    padding: 14px 16px;
    flex: 1 1 100%;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-size: 18px;
    font-weight: 700;
    color: #111827;
    word-break: break-word;
    overflow-wrap: break-word;
  }
  .ingredient-note {
    margin-top: 12px;
    background: linear-gradient(135deg, #a71930 0%, #7f1d1d 100%);
    border: 1px solid #c41e3a;
    border-radius: 12px;
    padding: 14px;
    text-align: center;
    color: #fff;
  }
  .ingredient-note-title {
    font-size: 16px;
    font-weight: 800;
    line-height: 1.5;
    margin-bottom: 12px;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .ingredient-btn {
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    transition: all 0.3s ease;
  }
  .ingredient-btn:hover {
    background: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.5);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
  .ingredient-btn:active {
    transform: translateY(0);
  }
  .other-ingredients {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.2);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .ingredient-item {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .ingredient-icon {
    color: #fcd34d;
    font-weight: bold;
    flex-shrink: 0;
  }
  .receipt-preview {
    text-align: center;
    margin-top: 8px;
  }
  .receipt-preview-label {
    font-size: 11px;
    color: #9ca3af;
    margin-bottom: 6px;
    letter-spacing: .02em;
  }
  .receipt-paper {
    display: inline-block;
    background: #fff;
    border: 1px dashed #d1d5db;
    border-radius: 4px;
    padding: 10px 16px;
    min-width: 140px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
  }
  .receipt-logo {
    width: 84px;
    height: 84px;
    object-fit: contain;
    display: block;
    margin: 0 auto 6px;
  }
  .receipt-eisa {
    font-size: 18px;
    font-weight: 800;
    letter-spacing: .06em;
    color: #111827;
    margin: 4px 0 8px;
    font-family: 'Courier New', monospace;
  }
  .receipt-text {
    font-size: 12px;
    color: #374151;
    margin: 2px 0;
    font-family: 'Courier New', monospace;
  }
</style>
