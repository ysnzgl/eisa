<script>
  export let puls =
    "M0,100 L120,100 L140,70 L152,130 L164,100 L184,100 L200,50 L212,150 L224,100 L268,100 L294,210 L300,190 L306,10 L332,100 L376,100 L388,50 L400,150 L412,100 L436,100 L448,70 L460,130 L472,100 L600,100";
</script>

<div class="heartbeat-animation" aria-hidden="true">
  <svg
    class="heartbeat-svg"
    viewBox="0 0 600 240"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Arka plan EKG çizgisi (düşük opaklık, beyaz) - 5 pik -->
    <path
      class="heartbeat-baseline"
      d={puls}
      fill="none"
      stroke="rgba(255, 255, 255, 0.2)"
      stroke-width="5"
    />

    <!-- Hareketli ışık kısmı (5 pik: küçük-orta-BÜYÜK şimşek-orta-küçük) -->
    <path
      class="heartbeat-pulse"
      d={puls}
      fill="none"
      stroke="url(#heartbeat-gradient)"
      stroke-width="10"
      stroke-linecap="round"
    />

    <!-- Gradient tanımlama (beyaz) -->
    <defs>
      <linearGradient id="heartbeat-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="rgba(255, 255, 255, 0)" />
        <stop offset="30%" stop-color="rgba(255, 255, 255, 0.6)" />
        <stop offset="50%" stop-color="rgba(255, 255, 255, 1)" />
        <stop offset="70%" stop-color="rgba(255, 255, 255, 0.6)" />
        <stop offset="100%" stop-color="rgba(255, 255, 255, 0)" />
      </linearGradient>
    </defs>
  </svg>

  <!-- Merkezden yayılan halkalar (beyaz) -->
  <div class="heartbeat-rings">
    <div class="heartbeat-ring heartbeat-ring--1"></div>
    <div class="heartbeat-ring heartbeat-ring--2"></div>
    <div class="heartbeat-ring heartbeat-ring--3"></div>
  </div>

  <!-- Merkez glow (beyaz) -->
  <div class="heartbeat-center-glow"></div>
</div>

<style>
  .heartbeat-animation {
    position: absolute;
    top: 35%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: clamp(580px, 35vw, 680px);
    height: clamp(580px, 35vw, 680px);
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    z-index: 0;
  }

  .heartbeat-svg {
    position: absolute;
    width: 100%;
    max-width: 600px;
    height: auto;
    opacity: 0.9;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }

  .heartbeat-baseline {
    /* Sabit arka plan çizgisi */
  }

  .heartbeat-pulse {
    stroke-dasharray: 1400;
    stroke-dashoffset: 1400;
    animation: heartbeat-pulse-wave 2.8s ease-in-out infinite;
  }

  .smile-curve {
    animation: smile-fade 2.8s ease-in-out infinite;
  }

  @keyframes heartbeat-pulse-wave {
    0% {
      stroke-dashoffset: 1400;
      opacity: 0.3;
    }
    15% {
      stroke-dashoffset: 1050;
      opacity: 1;
    }
    35% {
      stroke-dashoffset: 500;
      opacity: 1;
    }
    50% {
      stroke-dashoffset: 0;
      opacity: 0.7;
    }
    100% {
      stroke-dashoffset: -400;
      opacity: 0.2;
    }
  }

  @keyframes smile-fade {
    0%,
    100% {
      opacity: 0;
    }
    35%,
    55% {
      opacity: 1;
    }
    70% {
      opacity: 0.4;
    }
  }

  /* Merkezden yayılan halkalar (beyaz) */
  .heartbeat-rings {
    position: absolute;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .heartbeat-ring {
    position: absolute;
    border: 2px solid rgba(255, 255, 255, 0.5);
    border-radius: 50%;
    pointer-events: none;
  }

  .heartbeat-ring--1 {
    width: 140px;
    height: 140px;
    animation: heartbeat-ripple 2.8s ease-out infinite;
    animation-delay: 0s;
  }

  .heartbeat-ring--2 {
    width: 140px;
    height: 140px;
    animation: heartbeat-ripple 2.8s ease-out infinite;
    animation-delay: 0.15s;
  }

  .heartbeat-ring--3 {
    width: 140px;
    height: 140px;
    animation: heartbeat-ripple 2.8s ease-out infinite;
    animation-delay: 0.3s;
  }

  @keyframes heartbeat-ripple {
    0% {
      width: 140px;
      height: 140px;
      opacity: 0;
    }
    12% {
      opacity: 0.7;
    }
    30% {
      opacity: 0.9;
    }
    60% {
      width: 340px;
      height: 340px;
      opacity: 0.3;
    }
    100% {
      width: 460px;
      height: 460px;
      opacity: 0;
    }
  }

  /* Merkez glow efekti (beyaz) */
  .heartbeat-center-glow {
    position: absolute;
    width: 160px;
    height: 160px;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      rgba(255, 255, 255, 0.18) 0%,
      rgba(255, 255, 255, 0.08) 40%,
      rgba(255, 255, 255, 0) 70%
    );
    animation: heartbeat-glow-pulse 2.8s ease-in-out infinite;
  }

  @keyframes heartbeat-glow-pulse {
    0%,
    100% {
      transform: scale(0.9);
      opacity: 0.3;
    }
    20% {
      transform: scale(1.2);
      opacity: 0.9;
    }
    35% {
      transform: scale(1.1);
      opacity: 0.7;
    }
    55% {
      transform: scale(1);
      opacity: 0.4;
    }
  }

  /* Hareket azaltılması tercih edilirse animasyonları durdur */
  @media (prefers-reduced-motion: reduce) {
    .heartbeat-pulse {
      animation: none;
      stroke-dashoffset: 700;
      opacity: 0.7;
    }
    .heartbeat-ring {
      animation: none;
      width: 240px;
      height: 240px;
      opacity: 0.4;
    }
    .heartbeat-center-glow {
      animation: none;
      opacity: 0.4;
    }
    .smile-curve {
      animation: none;
      opacity: 0.6;
    }
  }
</style>
