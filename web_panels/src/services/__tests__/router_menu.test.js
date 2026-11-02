/**
 * Router + AdminLayout menü — kaldırılan/eklenen rota ve menü testleri.
 */
import { describe, it, expect, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const routerSrc = readFileSync(resolve(__dirname, '../../router/index.js'), 'utf8');
const layoutSrc = readFileSync(resolve(__dirname, '../../views/admin/AdminLayout.vue'), 'utf8');

describe('Router rotaları', () => {
  it('yeni rota /admin/kiosk-sponsorships mevcut', () => {
    expect(routerSrc).toContain("path: 'kiosk-sponsorships'");
    expect(routerSrc).toContain('KioskSponsorship.vue');
  });

  it('/admin/campaigns SponsorshipDefinitions.vue\'ye yönlenir', () => {
    expect(routerSrc).toContain('SponsorshipDefinitions.vue');
    expect(routerSrc).not.toContain('CampaignWizard.vue');
  });

  it('kaldırılan rotalar yok (playlists, pricing)', () => {
    expect(routerSrc).not.toContain("path: 'playlists'");
    expect(routerSrc).not.toContain("path: 'pricing'");
    expect(routerSrc).not.toContain('PlaylistEditor.vue');
    expect(routerSrc).not.toContain('PricingMatrixConfigurator.vue');
  });
});

describe('AdminLayout menüsü', () => {
  it('Kiosk Sponsorluk kiosk-sponsorships rotasına gider ve sponsorluk grubunda ilk sırada', () => {
    const kioskIdx = layoutSrc.indexOf("/admin/kiosk-sponsorships");
    const defsIdx = layoutSrc.indexOf("'/admin/campaigns'");
    expect(kioskIdx).toBeGreaterThan(-1);
    expect(defsIdx).toBeGreaterThan(-1);
    expect(kioskIdx).toBeLessThan(defsIdx);   // Kiosk Sponsorluk, Tanımlar'dan önce
    expect(layoutSrc).toContain('Kiosk Sponsorluk');
    expect(layoutSrc).toContain('Sponsorluk Tanımları');
  });

  it('kaldırılan menü öğeleri yok (Gelişmiş Manuel Yayın, Fiyat Matrisi)', () => {
    expect(layoutSrc).not.toContain('Gelişmiş Manuel Yayın');
    expect(layoutSrc).not.toContain('Fiyat Matrisi');
    expect(layoutSrc).not.toContain('/admin/playlists');
    expect(layoutSrc).not.toContain('/admin/pricing');
  });
});
