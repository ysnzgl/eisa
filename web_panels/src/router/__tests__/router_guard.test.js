/**
 * Router guard — editor yalnız Web Sitesi modülüne girebilir; mevcut
 * superadmin / pharmacist akışları bozulmaz.
 */
import { describe, it, expect, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

vi.mock('../../services/api', () => ({
  http: { defaults: { baseURL: '' }, get: vi.fn(), post: vi.fn() },
  login: vi.fn(),
  logout: vi.fn(),
}));

import router, { yetkiKontrolu } from '../index.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const layoutSrc = readFileSync(resolve(__dirname, '../../views/admin/AdminLayout.vue'), 'utf8');

const auth = (role, extra = {}) => ({ role, isAuthenticated: !!role, panelKisitli: false, ...extra });
const hedef = (path) => router.resolve(path);

describe('Web Sitesi rotaları', () => {
  it.each([
    '/admin/web-sitesi', '/admin/web-sitesi/sayfalar/3', '/admin/web-sitesi/menuler', '/admin/web-sitesi/blog',
    '/admin/web-sitesi/blog/yeni', '/admin/web-sitesi/medya', '/admin/web-sitesi/basvurular', '/admin/web-sitesi/ayarlar',
  ])('%s superadmin + editor rolleriyle eşleşir', (path) => {
    const r = hedef(path);
    expect(r.matched.length).toBeGreaterThan(1);
    expect(r.matched[0].path).toBe('/admin/web-sitesi');
    expect(r.meta.roles).toEqual(['superadmin', 'editor']);
  });

  it("'/admin' altındaki sayfalar hâlâ yalnız superadmin", () => {
    for (const p of ['/admin', '/admin/users', '/admin/devices']) {
      expect(hedef(p).meta.roles).toEqual(['superadmin']);
    }
  });
});

describe('yetkiKontrolu', () => {
  it('editor web sitesi rotalarına girer', () => {
    expect(yetkiKontrolu(hedef('/admin/web-sitesi/sayfalar/1'), auth('editor'))).toBe(true);
    expect(yetkiKontrolu(hedef('/admin/web-sitesi'), auth('editor'))).toBe(true);
  });

  it('editor /admin ve /pharmacist altındaki diğer sayfalara giremez → web sitesine yönlenir', () => {
    for (const p of ['/admin', '/admin/users', '/admin/abonelik', '/pharmacist', '/pharmacist/qr']) {
      expect(yetkiKontrolu(hedef(p), auth('editor'))).toEqual({ path: '/admin/web-sitesi' });
    }
  });

  it('superadmin hem /admin hem web sitesine girer', () => {
    expect(yetkiKontrolu(hedef('/admin/users'), auth('superadmin'))).toBe(true);
    expect(yetkiKontrolu(hedef('/admin/web-sitesi/ayarlar'), auth('superadmin'))).toBe(true);
  });

  it('eczacı web sitesine giremez; mevcut kısıtlı panel akışı korunur', () => {
    expect(yetkiKontrolu(hedef('/admin/web-sitesi'), auth('pharmacist'))).toEqual({ path: '/login' });
    expect(yetkiKontrolu(hedef('/pharmacist/qr'), auth('pharmacist'))).toBe(true);
    expect(yetkiKontrolu(hedef('/pharmacist/qr'), auth('pharmacist', { panelKisitli: true })))
      .toEqual({ path: '/pharmacist/hesabim' });
  });

  it('oturumsuz kullanıcı login sayfasına gider', () => {
    expect(yetkiKontrolu(hedef('/admin/web-sitesi'), auth(''))).toEqual({ path: '/login' });
    expect(yetkiKontrolu(hedef('/login'), auth(''))).toBe(true);
  });
});

describe('AdminLayout Web Sitesi menüsü', () => {
  it('Web Sitesi grubu ve başvuru rozeti tanımlı', () => {
    expect(layoutSrc).toContain("title: 'Web Sitesi'");
    expect(layoutSrc).toContain("'/admin/web-sitesi/basvurular'");
    expect(layoutSrc).toContain("badgeKey: 'basvuruYeni'");
    expect(layoutSrc).toContain('getBasvuruOzet');
  });
  it('editor yalnızca (sabit açık) Web Sitesi grubunu görür', () => {
    expect(layoutSrc).toMatch(/if \(isEditor\.value\) \{\s*return \[\{ key: 'web-sitesi',[^\]]*sabit: true, items: websiteNavItems \}\];/);
  });
  it('superadmin menüsü mantıksal gruplara ayrılmış ve Web Sitesi altında yardım var', () => {
    for (const baslik of ['Eczane & Kiosk', 'Kiosk İçeriği', 'Sponsorluk & Yayın', 'Destek & İletişim', 'Yönetim']) {
      expect(layoutSrc).toContain(`title: '${baslik}'`);
    }
    expect(layoutSrc).toContain("'/admin/web-sitesi/yardim'");
    // "Sitede ara" panelde değil web sitesinde arar → Web Sitesi grubunun ilk öğesi
    expect(layoutSrc).toMatch(/const websiteNavItems = \[\s*(\/\/[^\n]*\s*)?\{ eylem: 'ara'/);
    expect(layoutSrc).not.toContain('class="nav-arama"');
  });
});
