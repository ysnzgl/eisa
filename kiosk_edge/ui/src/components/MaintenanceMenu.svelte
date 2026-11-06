<script>
  import { createEventDispatcher } from 'svelte';
  import { performSystemAction } from '../lib/api.js';

  const dispatch = createEventDispatcher();
  let busy = false;
  let error = '';
  let status = '';

  async function refresh() {
    busy = true;
    error = '';
    status = 'Sunucu ayarları ve içerikler yenileniyor…';
    try {
      await performSystemAction('refresh');
      status = 'Yenileme tamamlandı. Uygulama yeniden yükleniyor…';
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      error = err?.userMessage || err?.message || 'İşlem tamamlanamadı.';
      status = '';
      busy = false;
    }
  }
</script>

<div class="maintenance-backdrop" role="presentation">
  <dialog class="maintenance-modal" open aria-labelledby="maintenance-title">
    <div class="maintenance-icon"><i class="fa-solid fa-screwdriver-wrench"></i></div>
    <h2 id="maintenance-title">Cihaz Bakımı</h2>
    <p>Bir bakım işlemi seçin.</p>
    <button class="primary" disabled={busy} on:click={refresh}>
      <i class="fa-solid fa-arrows-rotate"></i>
      <span><strong>Uygulamayı yenile</strong><small>Ayarları ve içerikleri sunucudan tekrar çeker</small></span>
    </button>
    <button class="secondary" disabled={busy} on:click={() => dispatch('close')}>Kapat</button>
    {#if status}<div class="status"><i class="fa-solid fa-spinner fa-spin"></i>{status}</div>{/if}
    {#if error}<div class="error"><i class="fa-solid fa-circle-exclamation"></i>{error}</div>{/if}
  </dialog>
</div>

<style>
  .maintenance-backdrop { position: fixed; inset: 0; z-index: 15000; display: grid; place-items: center; padding: 24px; background: rgba(15, 23, 42, 0.78); }
  .maintenance-modal { width: min(92vw, 520px); padding: 30px; border: 0; border-radius: 22px; text-align: center; color: #1f2937; background: #fff; box-shadow: 0 24px 80px rgba(0,0,0,.38); }
  .maintenance-icon { margin-bottom: 10px; color: #b1121b; font-size: 34px; }
  h2 { margin: 0; font-size: 27px; }
  p { margin: 8px 0 22px; color: #64748b; }
  button { display: flex; width: 100%; min-height: 58px; margin-top: 10px; padding: 12px 18px; align-items: center; justify-content: center; gap: 14px; border: 1px solid #dbe2ea; border-radius: 13px; color: #1f2937; background: #f8fafc; font: inherit; font-weight: 700; cursor: pointer; }
  button i { width: 24px; font-size: 20px; }
  button span { display: flex; flex-direction: column; text-align: left; }
  button small { margin-top: 3px; color: #64748b; font-size: 12px; font-weight: 500; }
  button.primary { color: #fff; border-color: #b1121b; background: #b1121b; }
  button.primary small { color: rgba(255,255,255,.82); }
  button.secondary { min-height: 46px; color: #64748b; border-color: transparent; background: transparent; }
  button:disabled { opacity: .55; cursor: wait; }
  .status, .error { display: flex; margin-top: 18px; padding: 12px; align-items: center; justify-content: center; gap: 9px; border-radius: 10px; font-size: 14px; }
  .status { color: #1d4ed8; background: #eff6ff; }
  .error { color: #b91c1c; background: #fef2f2; }
</style>
