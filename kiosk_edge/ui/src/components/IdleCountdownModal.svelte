<script>
  import { createEventDispatcher } from 'svelte';

  export let remaining = 5;
  const dispatch = createEventDispatcher();
</script>

<div class="idle-countdown-backdrop" role="presentation">
  <dialog class="idle-countdown-modal" open aria-labelledby="idle-countdown-title">
    <div class="idle-countdown-icon" aria-hidden="true"><i class="fa-solid fa-clock"></i></div>
    <h2 id="idle-countdown-title">İşleminiz devam ediyor mu?</h2>
    <p>İşleminiz <strong>{remaining}</strong> saniye içinde ana ekrana dönecek.</p>
    <button type="button" on:click={() => dispatch('continue')}>
      <i class="fa-solid fa-hand-pointer"></i>
      Devam Et
    </button>
    <button type="button" class="idle-countdown-return" on:click={() => dispatch('returnToIdle')}>Ana ekrana dön</button>
  </dialog>
</div>

<style>
  .idle-countdown-backdrop {
    position: fixed;
    inset: 0;
    z-index: 12000;
    display: grid;
    place-items: center;
    padding: 1.5rem;
    background: rgba(15, 23, 42, 0.68);
  }
  .idle-countdown-modal {
    width: min(92vw, 460px);
    padding: 2rem;
    text-align: center;
    color: #1f2937;
    background: #fff;
    border-radius: 1rem;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  }
  .idle-countdown-icon { color: #b1121b; font-size: 2rem; margin-bottom: 0.75rem; }
  h2 { margin: 0; font-size: 1.35rem; }
  p { margin: 0.65rem 0 1.4rem; color: #4b5563; font-size: 1rem; }
  p strong { color: #b1121b; font-size: 1.25em; }
  button {
    width: 100%; min-height: 52px; border: 0; border-radius: 0.55rem;
    color: white; background: #b1121b; font: inherit; font-weight: 700; cursor: pointer;
  }
  .idle-countdown-return { min-height: auto; margin-top: 0.7rem; padding: 0.45rem; color: #6b7280; background: transparent; font-size: 0.85rem; }
</style>
