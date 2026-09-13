/** Idle ses listesinin ekran/etkilesimden bagimsiz, test edilebilir durum makinesi. */
export function isIdleAudioAllowed(config, now = new Date()) {
  if (config?.idle_audio_schedule_mode !== 'BUSINESS_HOURS') return true;
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23',
  }).formatToParts(now).reduce((out, part) => ({ ...out, [part.type]: part.value }), {});
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  if (config?.idle_audio_play_on_duty && (config?.idle_audio_duty_dates || []).includes(date)) return true;
  return Number(parts.hour) >= 8 && Number(parts.hour) < 19;
}

export function formatIdleAudioDebugText(state) {
  if (!state?.enabled || !state?.fileCount) return 'Kapalı';
  if (!state.allowedNow) return 'Mesai dışı';
  if (state.playing) return 'Çalıyor';
  if (state.remainingSeconds === null || state.remainingSeconds === undefined) return '-- sn';
  return `${Math.max(0, state.remainingSeconds)} sn`;
}

export function createIdleAudioController({ play, stop, onPlayingChange = () => {} }) {
  let timer = null;
  let timerDueAt = null;
  let active = false;
  let playing = false;
  let nextIndex = 0;
  let config = null;
  let playlistKey = '';
  let scheduleKey = '';
  let cycleToken = 0;

  function files() {
    const configured = config?.idle_audio?.files;
    if (Array.isArray(configured) && configured.length) return configured.filter((item) => item?.media_url);
    return config?.idle_audio?.media_url
      ? [{ id: 'legacy', media_url: config.idle_audio.media_url }]
      : [];
  }

  function clearTimer() {
    if (timer) clearTimeout(timer);
    timer = null;
    timerDueAt = null;
  }

  function stopPlayback() {
    clearTimer();
    cycleToken += 1;
    playing = false;
    stop();
    onPlayingChange(false);
  }

  function canPlay() {
    return active && config?.idle_audio?.enabled && files().length > 0;
  }

  function schedule(delaySeconds) {
    clearTimer();
    if (!canPlay() || playing) return;
    const token = cycleToken;
    timerDueAt = Date.now() + (Math.max(1, delaySeconds) * 1000);
    timer = setTimeout(async () => {
      timer = null;
      timerDueAt = null;
      const playlist = files();
      if (!canPlay() || !playlist.length || token !== cycleToken) return;
      if (!isIdleAudioAllowed(config)) {
        schedule(60);
        return;
      }
      const item = playlist[nextIndex % playlist.length];
      nextIndex = (nextIndex + 1) % playlist.length;
      try {
        await play(item);
        if (!canPlay() || token !== cycleToken) {
          stop();
          return;
        }
        playing = true;
        onPlayingChange(true);
      } catch {
        if (canPlay() && token === cycleToken) {
          schedule(config?.idle_audio_repeat_seconds || 300);
        }
      }
    }, Math.max(1, delaySeconds) * 1000);
  }

  function initialDelaySeconds() {
    const configuredDelay = config?.idle_audio_delay_seconds || 1200;
    const repeatDelay = config?.idle_audio_repeat_seconds || 300;
    const lastQrCreatedAt = config?.idle_audio_last_qr_created_at;
    const lastQrMs = lastQrCreatedAt ? Date.parse(lastQrCreatedAt) : Number.NaN;
    if (!Number.isFinite(lastQrMs)) return configuredDelay;
    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - lastQrMs) / 1000));
    if (elapsedSeconds < configuredDelay) return configuredDelay - elapsedSeconds;
    return repeatDelay;
  }

  function stopCycle() {
    stopPlayback();
  }

  return {
    update(nextActive, nextConfig) {
      const nextFiles = Array.isArray(nextConfig?.idle_audio?.files) ? nextConfig.idle_audio.files : [];
      const nextPlaylistKey = JSON.stringify({
        enabled: nextConfig?.idle_audio?.enabled,
        files: nextFiles.map((item) => [item?.id, item?.media_url]),
        legacyUrl: nextConfig?.idle_audio?.media_url,
      });
      const nextScheduleKey = JSON.stringify({
        enabled: nextConfig?.idle_audio?.enabled,
        files: nextFiles.map((item) => [item?.id, item?.media_url]),
        legacyUrl: nextConfig?.idle_audio?.media_url,
        delay: nextConfig?.idle_audio_delay_seconds,
        repeat: nextConfig?.idle_audio_repeat_seconds,
        scheduleMode: nextConfig?.idle_audio_schedule_mode,
        playOnDuty: nextConfig?.idle_audio_play_on_duty,
        dutyDates: nextConfig?.idle_audio_duty_dates,
        lastQrCreatedAt: nextConfig?.idle_audio_last_qr_created_at,
      });
      const activeChanged = active !== nextActive;
      const playlistChanged = playlistKey !== nextPlaylistKey;
      const scheduleChanged = scheduleKey !== nextScheduleKey;
      active = nextActive;
      config = nextConfig;
      playlistKey = nextPlaylistKey;
      scheduleKey = nextScheduleKey;
      if (playlistChanged) nextIndex = 0;
      if (!active) {
        stopCycle();
      } else if (activeChanged) {
        stopCycle();
        schedule(initialDelaySeconds());
      } else if (playlistChanged || scheduleChanged) {
        stopCycle();
        schedule(initialDelaySeconds());
      }
    },
    interact() {
      if (!active || !playing) return;
      // Idle ekrandaki tek bir dokunus ses dongusunu kalici olarak susturmasin.
      // Gercek ekran gecisi update(false, ...) ile zamanlayiciyi zaten kapatir;
      // bekleyen timer dokunustan etkilenmez. Calan ses kesilirse siradaki dosya
      // normal devam araligindan sonra calar ve liste basi sifirlanmaz.
      stopCycle();
      schedule(config?.idle_audio_repeat_seconds || 300);
    },
    ended() {
      if (!playing) return;
      playing = false;
      onPlayingChange(false);
      schedule(config?.idle_audio_repeat_seconds || 300);
    },
    getDebugState(now = Date.now()) {
      const playlist = files();
      return {
        active,
        enabled: config?.idle_audio?.enabled === true,
        fileCount: playlist.length,
        playing,
        allowedNow: isIdleAudioAllowed(config),
        remainingSeconds: timerDueAt === null ? null : Math.max(0, Math.ceil((timerDueAt - now) / 1000)),
      };
    },
    destroy: stopPlayback,
  };
}
