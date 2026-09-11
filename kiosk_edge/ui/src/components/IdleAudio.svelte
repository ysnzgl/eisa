<script>
  import { onDestroy } from 'svelte';
  import { deviceConfig } from '../lib/deviceConfigStore.js';
  import { logger } from '../lib/logger.js';
  import { createIdleAudioController } from '../lib/idleAudioController.js';

  export let active = false;

  let audioElement = null;
  let isPlaying = false;

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
    onPlayingChange: (value) => { isPlaying = value; },
  });

  function onImmediateInteraction() {
    controller.interact();
  }

  $: controller.update(active, $deviceConfig);

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

<style>
  .idle-audio-indicator {
    position: fixed;
    top: 22px;
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

  @keyframes audioPulse {
    0%, 100% { transform: scale(1); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24); }
    50% { transform: scale(1.05); box-shadow: 0 8px 28px rgba(177, 18, 27, 0.42); }
  }

  @media (prefers-reduced-motion: reduce) {
    .idle-audio-indicator { animation: none; }
  }
</style>
