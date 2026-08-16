<script>
  // İlan olmadigi her yerde gosterilen sik, donen "Bu Alana İlan
  // Verebilirsiniz" tasarimi. Hem reklam bandinda (AdStrip) hem de ekran
  // koruyucuda (IdleScreen) kullanilir.
  //
  // large varyanti (idle/attractor): heartbeat animasyonu + üstte başlık (fade),
  // altta metin (daktilo) + sabit CTA. Başlık/metin idle içeriklerinden gelir
  // (İçerik Yönetimi). İçerik yoksa yalnız heartbeat + CTA + sponsor gösterilir.
  import { onDestroy } from 'svelte';
  import Logo from './Logo.svelte';
  import HeartbeatAnimation from './HeartbeatAnimation.svelte';
  import { currentIdleContent } from '../lib/idleContentStore.js';

  /** Buyuk kart boyutu icin true (idle/attractor kullanimi). */
  export let large = false;
  /** Container konumlandirmayi yonetirken background/inset kaldirmak icin true. */
  export let floatCard = false;

  // ── İdle içerik: başlık fade + metin daktilo ──
  let idle = null;
  let typedText = '';
  let typingActive = false;
  let titleKey = 0;
  let rafId = null;
  let lastId = null;

  const prefersReducedMotion = () =>
    typeof window !== 'undefined'
    && !!window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;

  function cancelTyping() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    typingActive = false;
  }

  function startTyping(text) {
    cancelTyping();
    typedText = '';
    if (prefersReducedMotion()) { typedText = text; typingActive = false; return; }
    typingActive = true;
    // 3.5–4.5 sn; uzun metinde karakter hızı artar, toplam 4.5 sn'yi geçmez.
    const total = Math.min(4500, Math.max(3500, (text.length || 1) * 45));
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / total);
      typedText = text.slice(0, Math.floor(t * text.length));
      if (t < 1) {
        rafId = requestAnimationFrame(step);
      } else {
        typedText = text;
        typingActive = false;
        rafId = null;
      }
    };
    rafId = requestAnimationFrame(step);
  }

  function onContent(val) {
    if (!large) return;
    const id = val?.id ?? null;
    if (id === lastId) return; // aynı içerik → yeniden daktilo yok
    lastId = id;
    idle = val;
    titleKey += 1;
    if (!val) { cancelTyping(); typedText = ''; return; }
    startTyping(val.metin || '');
  }

  const unsub = currentIdleContent.subscribe(onContent);
  onDestroy(() => { cancelTyping(); unsub(); });
</script>

<div class="ad-promo" class:ad-promo--large={large} class:ad-promo--float={floatCard}>
  <span class="ad-promo-glow" aria-hidden="true"></span>

  <!-- Dekoratif kalp atışı animasyonu + idle içerik (yalnız large varyantında) -->
 
    <HeartbeatAnimation />
 {#if large}
    <div class="idle-layer" aria-hidden="true">
      {#if idle}
        {#key titleKey}
          <div class="idle-title-block">
            {#if idle.ikon}
              <div class="idle-kategori-ikon">
                <i class="fa-solid {idle.ikon}"></i>
              </div>
            {/if}
            <div class="idle-title">{idle.baslik}</div>
          </div>
        {/key}
        <div class="idle-text">
          <span class="idle-text-inner">{typedText}</span><span
            class="idle-caret" class:idle-caret--on={typingActive}></span>
        </div>
      {/if}

      <div class="idle-cta">
        <span class="idle-cta-line1">Size özel öneriler için</span>
        <span class="idle-cta-line2">
          <span class="idle-cta-finger">
            <i class="fa-solid fa-hand-pointer"></i>
            <span class="idle-cta-ring"></span>
            <span class="idle-cta-ring idle-cta-ring--2"></span>
          </span>
          <b>DOKUNUN</b>
        </span>
      </div>
    </div>
  {/if}

  <div class="ad-promo-card">
    <div class="ad-promo-badge">
      <i class="fa-solid fa-bullhorn"></i>
    </div>
    <div class="ad-promo-text">
      <span class="ad-promo-title">Bu alana sponsor olabilirsiniz</span>
      <span class="ad-promo-sub">
        <Logo height={large ? '20px' : '15px'} light class="ad-promo-logo" />
        <span>Sponsorluk Ağı · Eczane Ekranında Markanız</span>
      </span>
    </div>
  </div>
</div>

<style>
  .ad-promo {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 20px;
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
  .ad-promo--large {
    padding-bottom: 48px;
  }
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

  /* floatCard: container konumlandirir; background ve inset kaldirilir */
  .ad-promo--float {
    position: relative;
    inset: unset;
    background: transparent;
    overflow: visible;
  }

  /* Hareket azaltilmasi tercih edilirse animasyonlari sakinlestir */
  @media (prefers-reduced-motion: reduce) {
    .ad-promo-glow { animation-duration: 60s; }
    .ad-promo-card,
    .ad-promo-title,
    .ad-promo-badge { animation: none; }
    .idle-title-block { animation: none !important; opacity: 1; transform: translateX(-50%) !important; }
    .idle-title { animation: none !important; }
    .idle-caret { display: none; }
    .idle-cta-finger i { animation: none; }
    .idle-cta-ring { display: none; }
  }

  /* ── İdle içerik katmanı (başlık / metin / CTA) — yalnız large ── */
  .idle-layer {
    position: absolute;
    inset: 0;
    z-index: 2;
    pointer-events: none;
  }

  /* başlık + ikon bloğu: heartbeat'in hemen üstünde, alt kenar = heart top - 20px */
  .idle-title-block {
    position: absolute;
    bottom: calc(50% + 250px);
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    width: 95%;
    animation: idle-title-in 480ms ease-out both;
  }

  .idle-kategori-ikon {
    font-size: 72px;
    color: #e0444c;
    line-height: 1;
    filter: drop-shadow(0 0 18px rgba(224, 68, 76, 0.65));
    text-shadow: 0 0 32px rgba(224, 68, 76, 0.4);
  }

  .idle-title {
    width: 100%;
    text-align: center;
    color: #ffffff;
    font-weight: 800;
    font-size: 50px;
    line-height: 1.3;
    letter-spacing: 0.3px;
    text-shadow: 0 2px 18px rgba(0, 0, 0, 0.6);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    padding: 14px 28px;
    border: 2px solid #e0444c;
    border-radius: 14px;
    box-shadow: 0 0 28px rgba(224, 68, 76, 0.45), inset 0 0 24px rgba(224, 68, 76, 0.08);
    background: rgba(0, 0, 0, 0.18);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }

  .idle-text {
    position: absolute;
    top: 63.5%;
    left: 50%;
    transform: translateX(-50%);
    width: 95%;
    min-height: 150px;
    text-align: center;
    color: #e7ecf5;
    font-size: 35px;
    font-weight: 500;
    line-height: 1.4;
    text-shadow: 0 1px 10px rgba(0, 0, 0, 0.45);
  }
  .idle-text-inner { white-space: pre-wrap; }

  .idle-caret {
    display: inline-block;
    width: 3px;
    height: 1.05em;
    margin-left: 2px;
    vertical-align: -0.18em;
    background: #e0444c;
    opacity: 0;
  }
  .idle-caret--on { animation: idle-caret-blink 0.8s step-end infinite; }

  .idle-cta {
    position: absolute;
    /* metin altında: text top 63.5% + min-height 150px + bofsluk */
    top: calc(70.5% + 175px);
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    pointer-events: none;
  }

  .idle-cta-line1 {
    color: #e7ecf5;
    font-size: 34px;
    font-weight: 500;
    letter-spacing: 0.3px;
    text-align: center;
  }

  .idle-cta-line2 {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .idle-cta-line2 b {
    font-size: 46px;
    font-weight: 900;
    letter-spacing: 1px;
    background: linear-gradient(90deg, #e0444c 0%, #ff8a90 45%, #e0444c 90%);
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: idle-cta-shine 2.8s linear infinite;
  }

  .idle-cta-finger {
    position: relative;
    width: 52px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: none;
  }
  .idle-cta-finger i {
    color: #e0444c;
    font-size: 40px;
    filter: drop-shadow(0 0 8px rgba(224, 68, 76, 0.7));
    animation: idle-finger-press 1.6s ease-in-out infinite;
  }
  .idle-cta-ring {
    position: absolute;
    top: 4px;
    left: 50%;
    width: 16px;
    height: 16px;
    margin-left: -8px;
    border-radius: 50%;
    border: 2.5px solid rgba(224, 68, 76, 0.8);
    opacity: 0;
    animation: idle-cta-ripple 1.6s ease-out infinite;
  }
  .idle-cta-ring--2 { animation-delay: 0.55s; }

  @keyframes idle-title-in {
    from { opacity: 0; transform: translateX(-50%) translateY(12px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
  }
  @keyframes idle-caret-blink {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0; }
  }
  @keyframes idle-finger-press {
    0%, 100% { transform: translateY(0); }
    45%      { transform: translateY(4px); }
  }
  @keyframes idle-cta-ripple {
    0%   { opacity: 0.7; transform: scale(0.4); }
    70%  { opacity: 0; transform: scale(2.1); }
    100% { opacity: 0; transform: scale(2.1); }
  }
  @keyframes idle-cta-shine {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
</style>
