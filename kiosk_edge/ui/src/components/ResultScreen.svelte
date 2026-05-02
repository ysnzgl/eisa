<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { result } from '../stores/kiosk.js';

  const dispatch = createEventDispatcher();

  let qrCanvas = null;

  export async function drawQR(code) {
    const QrCreator = (await import('qr-creator')).default;
    if (!qrCanvas) return;
    QrCreator.render(
      { text: code, radius: 0.5, ecLevel: 'M', fill: '#1a2e44', background: '#fff', size: 200 },
      qrCanvas,
    );
  }
</script>

<div class="screen">
  <div class="kiosk-header"><div class="kiosk-logo">e-<span>İSA</span></div></div>

  <div class="flex-grow-1 d-flex flex-column justify-content-center gap-3">
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
      <div class="result-ingredient-main" style="color:{$result?.isSensitive ? '#dc2626' : '#166534'}">
        {$result?.ana ?? ''}
      </div>
      <div class="result-ingredient-sub">{$result?.destek ?? ''}</div>
      {#if $result?.recs && $result.recs.length > 1}
        <div style="margin-top:12px; display:flex; flex-direction:column; gap:6px;">
          {#each $result.recs.slice(1) as rec}
            <div style="font-size:0.85rem; color:#166534; background:#dcfce7; border-radius:6px; padding:6px 10px;">
              <strong>{rec.primary}</strong>
              {#if rec.supportive}<span style="color:#6b7280;"> + {rec.supportive}</span>{/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="result-card" style="padding:24px; text-align:center;">
      <p class="qr-heading">
        <i class="fa-solid fa-ticket text-success"></i>
        Lütfen fişinizi/QR kodunuzu alınız
      </p>
      <div class="qr-box">
        <canvas bind:this={qrCanvas} style="border-radius:8px;"></canvas>
      </div>
      {#if $result?.qrCode}
        <p class="qr-code-text">{$result.qrCode}</p>
      {/if}
      <p class="qr-note">Bu QR kodu eczacınıza gösterin — bilgileriniz ekranına düşecek.</p>
    </div>
  </div>

  <div class="d-flex flex-column gap-2 mt-3">
    <button class="btn-touch btn-primary-touch" on:click={() => dispatch('done')}>
      <i class="fa-solid fa-house"></i> Bitir &amp; Başa Dön
    </button>
  </div>
</div>
