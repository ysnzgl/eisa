<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { result } from '../stores/kiosk.js';
  import Logo from './Logo.svelte';
  import { fetchSessionSyncStatus } from '../lib/api.js';

  const dispatch = createEventDispatcher();

  let qrCanvas = null;
  let syncDurum = null;
  let pollTimer = null;

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
    <Logo height="40px" />
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
        <div class="ingredient-area">
          {#each $result.recs as rec}
            <div class="ingredient-box">
              {rec.primary}{#if rec.supportive} + {rec.supportive}{/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="result-card" style="text-align:center;">
      <p class="qr-heading">
        <i class="fa-solid fa-ticket text-success"></i>
        Lütfen fişinizi/QR kodunuzu alınız
      </p>
      {#if $result?.qrCode}
        <div class="qr-box">
          <canvas bind:this={qrCanvas} style="border-radius:8px;"></canvas>
        </div>
        <p class="qr-code-text">{$result.qrCode}</p>
      {:else}
        <p style="color:#6B7280; font-size:14px; margin:12px 0;">QR kodu oluşturulamadı. Lütfen eczacıya danışın.</p>
      {/if}
      <p class="qr-note">Bu QR kodu eczacınıza gösterin — bilgileriniz ekranına düşecek.</p>
    </div>

    {#if $result?.baskiLogoUrl}
      <div class="receipt-preview">
        <p class="receipt-preview-label">
          <i class="fa-solid fa-print"></i> Termal fiş önizlemesi
        </p>
        <div class="receipt-paper">
          <img src={$result.baskiLogoUrl} alt="Barkod logosu" class="receipt-logo" />
          <p class="receipt-text">Saglikli gunler diler.</p>
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
      <i class="fa-solid fa-house"></i> Bitir &amp; Başa Dön
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
    flex: 1 1 calc(50% - 10px);
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
  .receipt-text {
    font-size: 12px;
    color: #374151;
    margin: 2px 0;
    font-family: 'Courier New', monospace;
  }
</style>
