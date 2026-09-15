<script>
  // İlan olmadigi her yerde gosterilen sik, donen "Bu Alana İlan
  // Verebilirsiniz" tasarimi. Hem reklam bandinda (AdStrip) hem de ekran
  // koruyucuda (IdleScreen) kullanilir.
  //
  // large varyanti (idle/attractor): heartbeat animasyonu + üstte başlık (fade),
  // altta metin (daktilo) + sabit CTA. Başlık/metin idle içeriklerinden gelir
  // (İçerik Yönetimi). İçerik yoksa yalnız heartbeat + CTA + sponsor gösterilir.
  import { onDestroy } from "svelte";
  import Logo from "./Logo.svelte";
  import HeartbeatAnimation from "./HeartbeatAnimation.svelte";
  import { currentIdleContent, eczaneAdi, kioskId } from "../lib/idleContentStore.js";
  import { normalizeIdleIcon } from "../lib/idleIcon.js";

  /** Buyuk kart boyutu icin true (idle/attractor kullanimi). */
  export let large = false;
  /** Container konumlandirmayi yonetirken background/inset kaldirmak icin true. */
  export let floatCard = false;

  // ── İdle içerik: başlık fade + metin daktilo ──
  let idle = null; // normal içerik veya null
  let typedText = "";
  let typingActive = false;
  let titleKey = 0;
  let rafId = null;
  let lastId = null;

  const prefersReducedMotion = () =>
    typeof window !== "undefined" &&
    !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

  function cancelTyping() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    typingActive = false;
  }

  function startTyping(text) {
    cancelTyping();
    typedText = "";
    if (prefersReducedMotion()) {
      typedText = text;
      typingActive = false;
      return;
    }
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
    if (id === lastId) return;

    lastId = id;
    idle = val;
    titleKey += 1;

    if (!val) {
      cancelTyping();
      typedText = "";
      return;
    }

    startTyping(val.metin || "");
  }

  const unsub = currentIdleContent.subscribe(onContent);
  onDestroy(() => {
    cancelTyping();
    unsub();
  });
</script>

<div
  class="ad-promo"
  class:ad-promo--large={large}
  class:ad-promo--float={floatCard}
>
  <span class="ad-promo-glow" aria-hidden="true"></span>
  {#if large}
 <div class="ai-assistant-label" style="top:18%">
        <span class="ai-assistant-text">SİZE UYGUN ÖNERİLER İÇİN</span>
      </div>
      <div class="idle-cta" style="top:23%">
        <!-- <span class="idle-cta-line1">Takviye Önerileri için</span> -->
        <span class="idle-cta-line2">
          <span class="idle-cta-finger">
            <i class="fa-solid fa-hand-pointer"></i>
            <span class="idle-cta-ring"></span>
            <span class="idle-cta-ring idle-cta-ring--2"></span>
          </span>
          <b>DOKUNUN</b>
        </span>
      </div>
      {/if}
  <!-- Dekoratif kalp atışı animasyonu + idle içerik (yalnız large varyantında) -->

  <HeartbeatAnimation onLight={large} />
  {#if large}
    <div class="idle-layer" aria-hidden="true">
      <div class="welcome-block">
        <div class="welcome-name">{$eczaneAdi || "Eczanemize"}</div>
        <div class="welcome-hos">HOŞGELDİNİZ</div>
      </div>

      {#if idle}
        {#key titleKey}
          <div class="idle-title-block">
            <div class="idle-kategori-ikon">
              <i class="fa-solid {normalizeIdleIcon(idle.ikon || idle.kategori_ikon)}"></i>
            </div>
            <div class="idle-title">
              <span class="idle-text-inner">{typedText}</span><span
                class="idle-caret"
                class:idle-caret--on={typingActive}
              ></span>
            </div>
          </div>
        {/key}
      {/if}
    </div>
  {/if}

  <div class="ad-promo-card">
    <div class="ad-promo-badge">
      <i class="fa-solid fa-bullhorn"></i>
    </div>
    <div class="ad-promo-text">
      <span class="ad-promo-title">Bu Alana Sponsor Olabilirsiniz</span>
      <span class="ad-promo-sub">
        <Logo height={large ? "50px" : "25px"} light={!large} class="ad-promo-logo" />
        <span>Sponsorluk Ağı · Eczane Ekranında Markanız</span>
      </span>
    </div>
  </div>

  {#if $kioskId}
    <span class="ad-promo-kiosk-name">{$kioskId}</span>
  {/if}
</div>

<style>
  .ad-promo {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 20px;
    background: radial-gradient(
      120% 140% at 50% 0%,
      #1b2436 0%,
      #0f1622 55%,
      #0b1019 100%
    );
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
      rgba(177, 18, 27, 0) 70deg,
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
    width: 75px;
    height: 75px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 1.4rem;
    background: linear-gradient(135deg, #b1121b 0%, #e0444c 100%);
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
    font-size: 40px;
    font-weight: 800;
    letter-spacing: 0.3px;
    background: linear-gradient(90deg, #ffffff 0%, #cfd6e4 45%, #ffffff 90%);
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: white;
    animation: ad-promo-shimmer 4.5s linear infinite;
  }

  .ad-promo-sub {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 500;
    letter-spacing: 0.4px;
    color: #9aa6bd;
    text-transform: uppercase;
  }

  /* ── Buyuk (ekran koruyucu) varyant ── */
  .ad-promo--large {
    padding-bottom: 48px;
    background:
      radial-gradient(circle at 50% 39%, rgba(177, 18, 27, 0.08), transparent 28%),
      radial-gradient(circle at 10% 8%, rgba(15, 143, 138, 0.07), transparent 24%),
      linear-gradient(180deg, #ffffff 0%, #fffafa 58%, #f9fafb 100%);
  }
  .ad-promo--large .ad-promo-glow {
    background: conic-gradient(
      from 0deg,
      transparent 0deg,
      rgba(177, 18, 27, 0) 65deg,
      rgba(177, 18, 27, 0.12) 120deg,
      rgba(15, 143, 138, 0.08) 180deg,
      rgba(177, 18, 27, 0.12) 240deg,
      transparent 305deg,
      transparent 360deg
    );
    opacity: 0.62;
  }
  .ad-promo--large .ad-promo-card {
    gap: 26px;
    padding: 28px 48px;
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid rgba(177, 18, 27, 0.16);
    box-shadow: 0 18px 45px rgba(82, 18, 24, 0.14);
  }
  .ad-promo--large .ad-promo-badge {
    width: 95px;
    height: 95px;
    font-size: 2.3rem;
  }
  .ad-promo--large .ad-promo-title {
    font-size: 50px;
    background: linear-gradient(90deg, #111827 0%, #b1121b 48%, #111827 100%);
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    -webkit-text-fill-color: transparent;
  }
  .ad-promo--large .ad-promo-sub {
    font-size: 22px;
    gap: 10px;
    color: #596273;
  }

  @keyframes ad-promo-spin {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes ad-promo-float {
    0%,
    100% {
      transform: translateY(0);
    }
    50% {
      transform: translateY(-5px);
    }
  }

  @keyframes ad-promo-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  @keyframes ad-promo-pulse {
    0% {
      box-shadow: 0 0 0 0 rgba(177, 18, 27, 0.5);
    }
    70% {
      box-shadow: 0 0 0 16px rgba(177, 18, 27, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(177, 18, 27, 0);
    }
  }

  /* floatCard: container konumlandirir; background ve inset kaldirilir */
  .ad-promo--float {
    position: relative;
    inset: unset;
    background: transparent;
    overflow: visible;
  }

  .ad-promo-kiosk-name {
    position: absolute;
    bottom: 10px;
    left: 14px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.3px;
    color: rgba(154, 166, 189, 0.6);
    pointer-events: none;
    z-index: 1;
  }

  .ad-promo--large .ad-promo-kiosk-name {
    color: rgba(55, 65, 81, 0.58);
  }

  /* Hareket azaltilmasi tercih edilirse animasyonlari sakinlestir */
  @media (prefers-reduced-motion: reduce) {
    .ad-promo-glow {
      animation-duration: 60s;
    }
    .ad-promo-card,
    .ad-promo-title,
    .ad-promo-badge {
      animation: none;
    }
    .ai-assistant-text {
      animation: none;
      opacity: 1;
      filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.6));
    }
    .idle-title-block {
      animation: none !important;
      opacity: 1;
      /* transform: translateX(-50%) !important; */
    }
    .idle-title {
      animation: none !important;
    }
    .idle-caret {
      display: none;
    }
    .idle-cta-finger i {
      animation: none;
    }
    .idle-cta-ring {
      display: none;
    }
  }

  /* ── İdle içerik katmanı (başlık / metin / CTA) — yalnız large ── */
  .idle-layer {
    position: absolute;
    inset: 0;
    z-index: 2;
    pointer-events: none;
  }

  /* Yapay Zeka Asistanı yazısı - HeartBeat'in üstünde */
  .ai-assistant-label {
    position: absolute;
    top: 15%;
    left: 50%;
    transform: translateX(-50%);
    z-index: 3;
    transform-origin: center;
    animation: ai-label-scale 2.8s ease-in-out infinite;
  }

  .ai-assistant-text {
    display: inline-block;
    /* 1080px'de 64px; küçük viewport'larda sığacak şekilde ölçeklenir */
    font-size: min(58px, 6vw);
    font-weight: 900;
    letter-spacing: min(4px, 0.37vw);
    text-transform: uppercase;
    background: linear-gradient(
      135deg,
      #ffffff 0%,
      #e7ecf5 25%,
      #ffffff 50%,
      #cfd6e4 75%,
      #ffffff 100%
    );
    background-size: 300% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    filter: drop-shadow(0 0 18px rgba(255, 255, 255, 0.5));
    animation: ai-label-glow 2.8s ease-in-out infinite;
    white-space: nowrap;
  }

  .ad-promo--large .ai-assistant-text {
    background: linear-gradient(
      135deg,
      #111827 0%,
      #4b5563 26%,
      #b1121b 50%,
      #4b5563 74%,
      #111827 100%
    );
    background-size: 300% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 8px 18px rgba(177, 18, 27, 0.12));
    animation: ai-label-glow-light 2.8s ease-in-out infinite;
  }

  @keyframes ai-label-glow-light {
    0%,
    100% {
      background-position: 200% 0;
      opacity: 0.82;
      filter: drop-shadow(0 6px 12px rgba(177, 18, 27, 0.1));
    }
    26% {
      background-position: 50% 0;
      opacity: 1;
      filter: drop-shadow(0 10px 24px rgba(177, 18, 27, 0.2));
    }
    50% {
      background-position: -50% 0;
      opacity: 0.9;
      filter: drop-shadow(0 7px 16px rgba(177, 18, 27, 0.14));
    }
  }

  /* Peak %26: heartbeat gradient merkezi (x=300) pika ulaştığı gerçek an */
  @keyframes ai-label-glow {
    0% {
      background-position: 200% 0;
      opacity: 0.55;
      filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.25)) brightness(0.85);
    }
    13% {
      opacity: 0.8;
      filter: drop-shadow(0 0 24px rgba(255, 255, 255, 0.55)) brightness(1.05);
    }
    26% {
      background-position: 50% 0;
      opacity: 1;
      filter: drop-shadow(0 0 90px rgba(255, 255, 255, 1))
        drop-shadow(0 0 50px rgba(255, 255, 255, 0.9)) brightness(1.8);
    }
    38% {
      background-position: 0% 0;
      opacity: 0.82;
      filter: drop-shadow(0 0 18px rgba(255, 255, 255, 0.38)) brightness(0.95);
    }
    100% {
      background-position: -200% 0;
      opacity: 0.55;
      filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.25)) brightness(0.85);
    }
  }

  /* scale ayrı animasyon — background-clip:text ile transform çakışmasın diye parent'ta */
  @keyframes ai-label-scale {
    0% {
      transform: translateX(-50%) scale(1);
    }
    13% {
      transform: translateX(-50%) scale(1.01);
    }
    26% {
      transform: translateX(-50%) scale(1.09);
    }
    38% {
      transform: translateX(-50%) scale(1.005);
    }
    100% {
      transform: translateX(-50%) scale(1);
    }
  }

  /* ── Welcome slide ─────────────────────────────────────────────────────────── */
  .welcome-block {
    position: absolute;
    bottom: 18%;
    left: 50%;    
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: clamp(5px, 0.8vh, 30px);
    width: 90%;
    animation: welcome-in 600ms cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  .welcome-name {
    font-size: clamp(26px, 5.5vw, 72px);
    font-weight: 900;
    letter-spacing: 1px;
    text-align: center;
    color: #ffffff;
    text-shadow:
      0 0 40px rgba(255, 255, 255, 0.5),
      0 3px 16px rgba(0, 0, 0, 0.5);
    line-height: 1.1;
    /* animation: welcome-fade-up 600ms 100ms cubic-bezier(0.22, 1, 0.36, 1) both; */
  }

  .ad-promo--large .welcome-name {
    color: #1f2937;
    text-shadow: 0 3px 16px rgba(17, 24, 39, 0.12);
  }

  .welcome-hos {
    font-size: clamp(40px, 5vw, 100px);
    font-weight: 900;
    letter-spacing: clamp(2px, 0.5vw, 8px);
    text-align: center;
    line-height: 1;
    background: linear-gradient(
      135deg,
      #ffffff 0%,
      #ffd6d8 30%,
      #e0444c 55%,
      #ff8a90 80%,
      #ffffff 100%
    );
    background-size: 300% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    filter: drop-shadow(0 0 24px rgba(224, 68, 76, 0.7));
    /* animation:
      welcome-fade-up 600ms 200ms cubic-bezier(0.22, 1, 0.36, 1) both,
      welcome-hos-shine 2.4s 800ms ease-in-out infinite; */
  }

  .ad-promo--large .welcome-hos {
    background: linear-gradient(
      135deg,
      #7f1d1d 0%,
      #b1121b 36%,
      #e0444c 62%,
      #7f1d1d 100%
    );
    background-size: 300% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 8px 18px rgba(177, 18, 27, 0.18));
  }

  .welcome-tagline {
    font-size: clamp(16px, 3vw, 44px);
    font-weight: 500;
    color: #cfd6e4;
    text-align: center;
    letter-spacing: 0.5px;
    text-shadow: 0 1px 10px rgba(0, 0, 0, 0.4);
    animation: welcome-fade-up 600ms 350ms cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  @keyframes welcome-in {
    from {
      opacity: 0;
      transform: translateX(-50%) scale(0.93);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) scale(1);
    }
  }
  @keyframes welcome-fade-up {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  @keyframes welcome-hos-shine {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  /* başlık + ikon bloğu: heartbeat'in hemen üstünde, alt kenar = heart top - 20px */
  .idle-title-block {
    position: absolute;
    bottom: 32%;
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
    width: 112px;
    height: 112px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 58px;
    color: #ffffff;
    background: #ed1c24;
    line-height: 1;
    border: 6px solid rgba(237, 28, 36, 0.14);
    background-clip: padding-box;
    box-shadow:
      0 14px 30px rgba(177, 18, 27, 0.22),
      0 0 0 1px rgba(237, 28, 36, 0.12);
  }

  .idle-title {
    min-height: 180px;
    width: 100%;
    text-align: center;
    color: #ffffff;
    font-weight: 800;
    font-size: 50px;
    line-height: 1.3;
    letter-spacing: 0.3px;
    text-shadow: 0 2px 18px rgba(0, 0, 0, 0.6);
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    padding: 14px 28px;
    border: 2px solid #e0444c;
    border-radius: 14px;
    box-shadow:
      0 0 28px rgba(224, 68, 76, 0.45),
      inset 0 0 24px rgba(224, 68, 76, 0.08);
    background: rgba(0, 0, 0, 0.18);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }

  .ad-promo--large .idle-title {
    color: #1f2937;
    text-shadow: none;
    border-color: rgba(177, 18, 27, 0.72);
    box-shadow:
      0 16px 38px rgba(82, 18, 24, 0.12),
      inset 0 0 24px rgba(177, 18, 27, 0.035);
    background: rgba(255, 255, 255, 0.88);
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
  .idle-text-inner {
    white-space: pre-wrap;
  }

  .idle-caret {
    display: inline-block;
    width: 3px;
    height: 1.05em;
    margin-left: 2px;
    vertical-align: -0.18em;
    background: #e0444c;
    opacity: 0;
  }
  .idle-caret--on {
    animation: idle-caret-blink 0.8s step-end infinite;
  }

  .idle-cta {
    position: absolute;
    /* metin altında: text top 63.5% + min-height 150px + bofsluk */
    top: 20%;
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
    font-size: 54px;
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
    font-size: 96px;
    font-weight: 800;
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
    width: 100px;
    height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: none;
  }
  .idle-cta-finger i {
    color: #fdfdfd;
    font-size: 90px;
    filter: drop-shadow(0 0 8px rgba(109, 105, 105, 0.7));
    animation: idle-finger-press 1.6s ease-in-out infinite;
  }
  .ad-promo--large .idle-cta-finger i {
    color: #b1121b;
    filter: drop-shadow(0 7px 12px rgba(177, 18, 27, 0.24));
  }
  .idle-cta-ring {
    position: absolute;
    top: 0px;
    left: 50%;
    width: 56px;
    height: 56px;
    margin-left: -40px;
    border-radius: 50%;
    border: 2.5px solid rgba(211, 197, 198, 0.8);
    opacity: 0;
    animation: idle-cta-ripple 1.6s ease-out infinite;
  }
  .ad-promo--large .idle-cta-ring {
    border-color: rgba(177, 18, 27, 0.52);
  }
  .idle-cta-ring--2 {
    animation-delay: 0.55s;
  }

  @keyframes idle-title-in {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(12px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
  @keyframes idle-caret-blink {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0;
    }
  }
  @keyframes idle-finger-press {
    0%,
    100% {
      transform: translateY(0);
    }
    45% {
      transform: translateY(18px) rotate(-10deg);
    }     
  }
  @keyframes idle-cta-ripple {
    0% {
      opacity: 0.7;
      transform: scale(0.4);
    }
    70% {
      opacity: 0;
      transform: scale(2.1);
    }
    100% {
      opacity: 0;
      transform: scale(2.1);
    }
  }
  @keyframes idle-cta-shine {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }
</style>
