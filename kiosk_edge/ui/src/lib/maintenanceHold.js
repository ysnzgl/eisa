export function createMaintenanceHold({
  durationMs = 10_000,
  onHoldingChange = () => {},
  onProgress = () => {},
  onShortPress = () => {},
  onLongPress = () => {},
} = {}) {
  let timer = null;
  let progressTimer = null;
  let startedAt = 0;

  function reportProgress() {
    const elapsedMs = Math.min(durationMs, Math.max(0, Date.now() - startedAt));
    const percent = Math.round((elapsedMs / durationMs) * 100);
    const remainingSeconds = Math.max(0, Math.ceil((durationMs - elapsedMs) / 1000));
    onProgress(percent, remainingSeconds);
  }

  function cancel() {
    if (timer) clearTimeout(timer);
    if (progressTimer) clearInterval(progressTimer);
    timer = null;
    progressTimer = null;
    onHoldingChange(false);
    onProgress(0, Math.ceil(durationMs / 1000));
  }

  return {
    begin() {
      if (timer) return;
      startedAt = Date.now();
      onHoldingChange(true);
      reportProgress();
      progressTimer = setInterval(reportProgress, 100);
      timer = setTimeout(() => {
        if (progressTimer) clearInterval(progressTimer);
        timer = null;
        progressTimer = null;
        onProgress(100, 0);
        onHoldingChange(false);
        onLongPress();
      }, durationMs);
    },
    end() {
      const wasShortPress = !!timer;
      cancel();
      if (wasShortPress) onShortPress();
    },
    cancel,
    destroy: cancel,
  };
}
