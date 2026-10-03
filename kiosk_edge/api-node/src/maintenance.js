/**
 * Uygulama yenilemesini tekilleştirir ve soguk acilistaki merkezi uzlastirma
 * adimlarini sirayla calistirir. Provision kimligi silinmez.
 */
export function createApplicationRefresher({
  db,
  settings,
  resolveRuntimeSettings,
  hasAppKeyCredentials,
  syncDeviceConfig,
  pullFromCentral,
  pingAndSyncPlaylist,
  pingAndSyncManifest,
}) {
  let inFlight = null;

  return function refreshApplication(log = console) {
    if (inFlight) return inFlight;
    inFlight = (async () => {
      const refreshedSettings = await resolveRuntimeSettings(db, settings, log);
      if (refreshedSettings.bootstrapDeviceConfig) {
        await syncDeviceConfig(db, refreshedSettings.bootstrapDeviceConfig, refreshedSettings, log);
      }
      if (!hasAppKeyCredentials(db)) {
        return { provisioned: false, synced: false };
      }
      await pullFromCentral(db, refreshedSettings, log);
      const ping = refreshedSettings.doohKioskAck ? pingAndSyncManifest : pingAndSyncPlaylist;
      await ping(db, refreshedSettings, log);
      return { provisioned: true, synced: true };
    })().finally(() => { inFlight = null; });
    return inFlight;
  };
}
