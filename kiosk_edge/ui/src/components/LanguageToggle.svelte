<script>
  // Kiosk kösesindeki dil butonu (TR / EN). Segment olarak iki dili gösterir;
  // secili dil vurgulanir. Idle ekranda dokunma akisi baslatmasin diye tiklama
  // olaylari burada durdurulur (bu eleman screen-saver'in kardesi, ust katman).
  import { language, setLanguage } from '../lib/i18n.js';

  function choose(lang, event) {
    event.stopPropagation();
    setLanguage(lang);
  }
</script>

<div class="lang-toggle" role="group" aria-label="Dil / Language">
  <button
    type="button"
    class="lang-btn"
    class:active={$language === 'tr'}
    aria-pressed={$language === 'tr'}
    on:click={(e) => choose('tr', e)}
    on:pointerdown|stopPropagation
  >TR</button>
  <span class="lang-sep" aria-hidden="true"></span>
  <button
    type="button"
    class="lang-btn"
    class:active={$language === 'en'}
    aria-pressed={$language === 'en'}
    on:click={(e) => choose('en', e)}
    on:pointerdown|stopPropagation
  >EN</button>
</div>

<style>
  .lang-toggle {
    position: fixed;
    top: 14px;
    right: 14px;
    z-index: 14000;
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 4px;
    border-radius: 999px;
    background: rgba(17, 24, 39, 0.72);
    backdrop-filter: blur(6px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
    pointer-events: auto;
    user-select: none;
  }
  .lang-btn {
    min-width: 46px;
    min-height: 40px;
    padding: 0 12px;
    border: 0;
    border-radius: 999px;
    background: transparent;
    color: rgba(255, 255, 255, 0.7);
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.04em;
    cursor: pointer;
    transition: background 0.18s ease, color 0.18s ease;
  }
  .lang-btn.active {
    background: #ed1c24;
    color: #fff;
    box-shadow: 0 2px 8px rgba(237, 28, 36, 0.45);
  }
  .lang-sep {
    width: 1px;
    height: 20px;
    background: rgba(255, 255, 255, 0.18);
  }
</style>
