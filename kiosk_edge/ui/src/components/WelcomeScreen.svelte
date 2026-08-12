<script>
  import { createEventDispatcher } from 'svelte';
  import ScreenHeader from './ScreenHeader.svelte';

  const dispatch = createEventDispatcher();
</script>

<div class="screen">
  <ScreenHeader />

  <div class="flex-grow-1 d-flex flex-column justify-content-center">
    <h2 class="screen-title text-center">Nasıl Yardımcı Olabilirim?</h2>
    <div class="d-flex flex-column gap-3">
      <button class="btn-touch btn-primary-touch btn-main-touch" on:click={() => dispatch('flowA')}>
        <i class="fa-solid fa-hand-pointer"></i>
        Şikayetimi Seç &amp; Soruları Cevapla
        <span class="btn-sub">Size uygun takviye önerisini alın ve QR fişinizi oluşturun.</span>
      </button>

      <div class="or-divider">VEYA</div>

      <button class="btn-touch btn-consult-touch btn-main-touch" on:click={() => dispatch('flowConsult')}>
        <i class="fa-solid fa-comments"></i>
        Eczacınıza Özel Danışın
        <span class="btn-sub">Kişisel konularınızı gizlilik içinde paylaşabilirsiniz.</span>
      </button>
    </div>
  </div>

  <div class="footer-note">
    <i class="fa-solid fa-shield-halved"></i>
    Bu sistem marka önermez. Verileriniz anonim tutulur.
  </div>
</div>
