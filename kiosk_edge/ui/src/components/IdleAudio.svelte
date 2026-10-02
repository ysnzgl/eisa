<script>
  import { onDestroy, onMount } from 'svelte';
  import { deviceConfig } from '../lib/deviceConfigStore.js';
  import { logger } from '../lib/logger.js';
  import { createIdleAudioController, formatIdleAudioDebugText } from '../lib/idleAudioController.js';

  export let active = false;
  export let lastQrCreatedAt = null;

  let audioElement = null;
  let isPlaying = false;
  let counterState = null;
  let counterText = 'Kapalı';
  let counterTimer = null;

  function stopElement() {
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
  }

  const controller = createIdleAudioController({
    play: async (file) => {
      if (!audioElement) throw new Error('Idle ses elementi hazır değil');
      audioElement.src = file.media_url;
      audioElement.load();
      audioElement.currentTime = 0;
      try {
        await audioElement.play();
      } catch (error) {
        logger.error('media_playback_failed', error?.message || 'Idle ses oynatılamadı', {
          component: 'IdleAudio',
        });
        throw error;
      }
    },
    stop: stopElement,
    onPlayingChange: (value) => {
      isPlaying = value;
      refreshCounterState();
    },
  });

  function refreshCounterState() {
    counterState = controller.getDebugState();
    counterText = formatIdleAudioDebugText(counterState);
  }

  function onImmediateInteraction() {
    controller.interact();
    refreshCounterState();
  }

  $: {
    controller.update(active, {
      ...$deviceConfig,
      idle_audio_last_qr_created_at: lastQrCreatedAt,
    });
    refreshCounterState();
  }

  onMount(() => {
    refreshCounterState();
    counterTimer = window.setInterval(refreshCounterState, 1000);
    return () => {
      if (counterTimer) window.clearInterval(counterTimer);
    };
  });

  onDestroy(controller.destroy);
</script>

<svelte:window on:pointerdown={onImmediateInteraction} on:keydown={onImmediateInteraction} />

<audio
  bind:this={audioElement}
  preload="auto"
  on:ended={controller.ended}
  on:error={controller.ended}
></audio>

{#if isPlaying && active}
  <div class="idle-audio-indicator" role="status" aria-label="Idle sesi çalıyor">
    <i class="fa-solid fa-volume-high" aria-hidden="true"></i>
  </div>
{/if}

{#if active && $deviceConfig.idle_audio_countdown_visible === true}
  <div class="idle-audio-counter" aria-label="Sese kalan süre">
    <span>Sese kalan</span>
    <strong>{counterText}</strong>
  </div>
{/if}

<style>
  .idle-audio-indicator {
    position: fixed;
    top: 78px;
    right: 22px;
    z-index: 10020;
    width: 48px;
    height: 48px;
    border-radius: 999px;
    display: grid;
    place-items: center;
    color: #fff;
    background: rgba(177, 18, 27, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.55);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
    pointer-events: none;
    animation: audioPulse 1.8s ease-in-out infinite;
  }

  .idle-audio-indicator i { font-size: 20px; }

  .idle-audio-counter {
    position: fixed;
    top: 10px;
    left: 10px;
    z-index: 10030;
    min-width: 76px;
    padding: 5px 7px;
    border-radius: 6px;
    color: rgba(255, 255, 255, 0.82);
    background: rgba(15, 23, 42, 0.38);
    border: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12);
    pointer-events: none;
    text-align: left;
    backdrop-filter: blur(3px);
  }

  .idle-audio-counter span {
    display: block;
    font-size: 8px;
    line-height: 1.1;
    color: rgba(255, 255, 255, 0.55);
  }

  .idle-audio-counter strong {
    display: block;
    margin-top: 2px;
    font-size: 13px;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  @keyframes audioPulse {
    0%, 100% { transform: scale(1); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24); }
    50% { transform: scale(1.05); box-shadow: 0 8px 28px rgba(177, 18, 27, 0.42); }
  }

  @media (prefers-reduced-motion: reduce) {
    .idle-audio-indicator { animation: none; }
  }
</style>
