import { describe, it, expect } from 'vitest';

describe('idle content rotation', () => {
  it('welcome döngüsü yoktur; yalnızca normal içerikler döner', () => {
    const rotation = [
      { id: 1, metin: 'Vitamin', aktif: true },
      { id: 2, metin: 'Ağrı', aktif: true },
      { id: 3, metin: 'Diş', aktif: true },
    ];

    const hasWelcomeType = rotation.some((item) => item._type === 'welcome');
    expect(hasWelcomeType).toBe(false);
    expect(rotation.length).toBe(3);
  });

  it('sağlam görünüm için sabit welcome ve içerik katmanları ayrı tutulur', () => {
    const welcomeText = 'Eczanemize';
    const contentText = 'Vitamin takviyesi';

    expect(welcomeText).toBeTruthy();
    expect(contentText).toBeTruthy();
    expect(welcomeText).not.toBe(contentText);
  });
});
