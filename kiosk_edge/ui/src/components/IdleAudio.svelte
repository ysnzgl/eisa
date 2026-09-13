<script>
  import { onDestroy, onMount } from 'svelte';
  import { deviceConfig } from '../lib/deviceConfigStore.js';
  import { logger } from '../lib/logger.js';
  import { createIdleAudioController, formatIdleAudioDebugText } from '../lib/idleAudioController.js';

  export let active = false;
  export let lastQrCreatedAt = null;

  const showDebugCounter = import.meta.env.DEV || import.meta.env.VITE_KIOSK_DEBUG === 'true';

  let audioElement = null;
  let isPlaying = false;
  let debugState = null;
  let debugText = 'Kapalı';
  let debugTimer = null;

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
      refreshDebugState();
    },
  });

  function refreshDebugState() {
    if (!showDebugCounter) return;
    debugState = controller.getDebugState();
    debugText = formatIdleAudioDebugText(debugState);
  }

  function onImmediateInteraction() {
    controller.interact();
    refreshDebugState();
  }

  $: {
    controller.update(active, {
      ...$deviceConfig,
      idle_audio_last_qr_created_at: lastQrCreatedAt,
    });
    refreshDebugState();
  }

  onMount(() => {
    if (!showDebugCounter) return undefined;
    refreshDebugState();
    debugTimer = window.setInterval(refreshDebugState, 1000);
    return () => {
      if (debugTimer) window.clearInterval(debugTimer);
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

{#if showDebugCounter && active}
  <div class="idle-audio-debug-counter" aria-label="Sese kalan süre">
    <span>Sese kalan</span>
    <strong>{debugText}</strong>
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

  .idle-audio-debug-counter {
    position: fixed;
    top: 18px;
    right: 18px;
    z-index: 10030;
    min-width: 118px;
    padding: 8px 10px;
    border-radius: 8px;
    color: #fff;
    background: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.35);
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.24);
    pointer-events: none;
    text-align: right;
    backdrop-filter: blur(6px);
  }

  .idle-audio-debug-counter span {
    display: block;
    font-size: 10px;
    line-height: 1.1;
    color: rgba(255, 255, 255, 0.72);
  }

  .idle-audio-debug-counter strong {
    display: block;
    margin-top: 3px;
    font-size: 18px;
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
