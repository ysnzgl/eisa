<script>
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();
</script>

<div class="screen">
  <div class="kiosk-header">
    <div class="kiosk-logo">e-<span>İSA</span></div>
    <div class="kiosk-subtitle">Eczane İçi Sağlık Asistanınız</div>
  </div>

  <div class="flex-grow-1 d-flex flex-column justify-content-center">
    <h2 class="screen-title text-center">Nasıl Yardımcı Olabilirim?</h2>
    <div class="d-flex flex-column gap-3">
      <button class="btn-touch btn-primary-touch" on:click={() => dispatch('flowA')}>
        <i class="fa-solid fa-hand-pointer"></i>
        Şikayetimi Seç &amp; Anket Çöz
        <span class="btn-sub">Takviye önerisi al, QR fiş al</span>
      </button>

      <div class="or-divider">VEYA</div>

      <button class="btn-touch btn-danger-touch" on:click={() => dispatch('flowB')}>
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
