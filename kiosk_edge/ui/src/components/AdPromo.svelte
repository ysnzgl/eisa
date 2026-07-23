<script>
  // İlan olmadigi her yerde gosterilen sik, donen "Bu Alana İlan
  // Verebilirsiniz" tasarimi. Hem reklam bandinda (AdStrip) hem de ekran
  // koruyucuda (IdleScreen) kullanilir.
  import Logo from './Logo.svelte';

  /** Buyuk (tam ekran / ekran koruyucu) varyant icin true. */
  export let large = false;
</script>

<div class="ad-promo" class:ad-promo--large={large}>
  <span class="ad-promo-glow" aria-hidden="true"></span>
  <div class="ad-promo-card">
    <div class="ad-promo-badge">
      <i class="fa-solid fa-bullhorn"></i>
    </div>
    <div class="ad-promo-text">
      <span class="ad-promo-title">Bu Alana İlan Verebilirsiniz</span>
      <span class="ad-promo-sub">
        <Logo height={large ? '20px' : '15px'} light class="ad-promo-logo" />
        <span>İlan Ağı · Eczane Ekranında Markanız</span>
      </span>
    </div>
  </div>
</div>

<style>
  .ad-promo {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
      radial-gradient(120% 140% at 50% 0%, #1b2436 0%, #0f1622 55%, #0b1019 100%);
    overflow: hidden;
  }

  /* Yavasca donen konik isik halkasi (elegant "donme" efekti) */
  .ad-promo-glow {
    position: absolute;
    width: 150%;
    aspect-ratio: 1;
    border-radius: 50%;
    background: conic-gradient(
      from 0deg,
      transparent 0deg,
      rgba(177, 18, 27, 0.0) 70deg,
      rgba(177, 18, 27, 0.35) 120deg,
      rgba(225, 60, 70, 0.18) 180deg,
      rgba(177, 18, 27, 0.35) 240deg,
      transparent 300deg,
      transparent 360deg
    );
    filter: blur(28px);
    opacity: 0.7;
    animation: ad-promo-spin 18s linear infinite;
    pointer-events: none;
  }

  .ad-promo-card {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 14px 26px;
    border-radius: 16px;
    background: rgba(17, 24, 39, 0.62);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    animation: ad-promo-float 6s ease-in-out infinite;
  }

  .ad-promo-badge {
    flex: none;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 1.4rem;
    background: linear-gradient(135deg, #B1121B 0%, #e0444c 100%);
    box-shadow: 0 0 0 0 rgba(177, 18, 27, 0.55);
    animation: ad-promo-pulse 2.6s ease-out infinite;
  }

  .ad-promo-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
    line-height: 1.2;
  }

  .ad-promo-title {
    font-size: 19px;
    font-weight: 700;
    letter-spacing: 0.3px;
    background: linear-gradient(90deg, #ffffff 0%, #cfd6e4 45%, #ffffff 90%);
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: ad-promo-shimmer 4.5s linear infinite;
  }

  .ad-promo-sub {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
    font-weight: 500;
    letter-spacing: 0.4px;
    color: #9aa6bd;
    text-transform: uppercase;
  }

  /* ── Buyuk (ekran koruyucu) varyant ── */
  .ad-promo--large .ad-promo-card {
    gap: 26px;
    padding: 28px 48px;
    border-radius: 22px;
  }
  .ad-promo--large .ad-promo-badge {
    width: 84px;
    height: 84px;
    font-size: 2.3rem;
  }
  .ad-promo--large .ad-promo-title { font-size: 34px; }
  .ad-promo--large .ad-promo-sub   { font-size: 16px; gap: 10px; }

  @keyframes ad-promo-spin {
    to { transform: rotate(360deg); }
  }

  @keyframes ad-promo-float {
    0%, 100% { transform: translateY(0); }
    50%      { transform: translateY(-5px); }
  }

  @keyframes ad-promo-shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  @keyframes ad-promo-pulse {
    0%   { box-shadow: 0 0 0 0 rgba(177, 18, 27, 0.5); }
    70%  { box-shadow: 0 0 0 16px rgba(177, 18, 27, 0); }
    100% { box-shadow: 0 0 0 0 rgba(177, 18, 27, 0); }
  }

  /* Hareket azaltilmasi tercih edilirse animasyonlari sakinlestir */
  @media (prefers-reduced-motion: reduce) {
    .ad-promo-glow { animation-duration: 60s; }
    .ad-promo-card,
    .ad-promo-title,
    .ad-promo-badge { animation: none; }
  }
</style>
