<script>
  // Idle CTA overlay. Medya artik kalici PlaylistPlayer'da (arkada, z-index:100);
  // bu katman seffaftir ve yalniz logo + "Baslamak icin dokunun" + dokunma
  // hedefi saglar. Burada video YOKTUR → idle<->oturum gecisinde kalici
  // oynaticidaki <video> DOM instance'i korunur.
  import { createEventDispatcher, onDestroy } from 'svelte';
  import Logo from './Logo.svelte';
  import { createMaintenanceHold } from '../lib/maintenanceHold.js';

  const dispatch = createEventDispatcher();
  const MAINTENANCE_HOLD_MS = 10_000;
  let holding = false;
  let holdProgress = 0;
  let holdRemainingSeconds = 10;
  const maintenanceHold = createMaintenanceHold({
    durationMs: MAINTENANCE_HOLD_MS,
    onHoldingChange: (value) => { holding = value; },
    onProgress: (progress, remainingSeconds) => {
      holdProgress = progress;
      holdRemainingSeconds = remainingSeconds;
    },
    onShortPress: () => dispatch('start'),
    onLongPress: () => dispatch('maintenance'),
  });

  function handleTap() {
    dispatch('start');
  }

  function beginMaintenanceHold(event) {
    if (Number.isInteger(event.pointerId)) {
      event.currentTarget?.setPointerCapture?.(event.pointerId);
    }
    maintenanceHold.begin();
  }

  function cancelMaintenanceHold() {
    maintenanceHold.cancel();
  }

  function finishMaintenanceHold() {
    maintenanceHold.end();
  }

  onDestroy(() => maintenanceHold.destroy());
</script>

<div
  class="screen-saver"
  on:click={handleTap}
  role="button"
  tabindex="0"
  on:keydown={(e) => e.key === 'Enter' && handleTap()}
>
  <!-- Logo + CTA -->
  <div class="ss-overlay-text">
    <div
      class:holding
      class="maintenance-trigger"
      role="button"
      tabindex="0"
      aria-label="Bakım menüsünü aç"
      on:pointerdown|stopPropagation={beginMaintenanceHold}
      on:pointerup|stopPropagation={finishMaintenanceHold}
      on:pointercancel|stopPropagation={cancelMaintenanceHold}
      on:click|stopPropagation
      on:contextmenu|preventDefault|stopPropagation
      on:keydown|stopPropagation={(event) => (event.key === 'Enter' || event.key === ' ') && beginMaintenanceHold(event)}
      on:keyup|stopPropagation={finishMaintenanceHold}
      on:blur={cancelMaintenanceHold}
    >
      <Logo height="100px" class="ss-logo-img" />
      {#if holding}
        <div class="maintenance-hold-feedback" style="--hold-progress: {holdProgress * 3.6}deg" aria-live="polite">
          <span class="maintenance-spinner" aria-hidden="true"></span>
          <strong>Bakım menüsü açılıyor</strong>
          <span>Basılı tut · {holdRemainingSeconds} sn</span>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .maintenance-trigger { position: relative; touch-action: none; outline: none; border-radius: 16px; }
  .maintenance-trigger.holding { transform: scale(0.985); }
  .maintenance-hold-feedback {
    position: absolute; inset: -22px -34px; z-index: 3;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    border-radius: 20px; color: #fff; background: rgba(15, 23, 42, 0.92);
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.32); pointer-events: none;
  }
  .maintenance-hold-feedback strong { margin-top: 9px; font-size: 18px; }
  .maintenance-hold-feedback > span:last-child { margin-top: 3px; color: #cbd5e1; font-size: 14px; }
  .maintenance-spinner {
    width: 42px; height: 42px; padding: 5px; border-radius: 50%;
    background: conic-gradient(#ef4444 var(--hold-progress), rgba(255,255,255,.18) 0);
    animation: maintenance-pulse 1s ease-in-out infinite alternate;
  }
  .maintenance-spinner::after {
    content: ''; display: block; width: 100%; height: 100%; border-radius: 50%;
    background: #0f172a url('../assets/eisa-logo-light.svg') center / 78% auto no-repeat;
  }
  @keyframes maintenance-pulse { from { transform: scale(.96); } to { transform: scale(1.05); } }
</style>
