// Backend kategori ikonlari `fa-bolt` veya `fa-solid fa-bolt` biciminde
// gelebilir. UI yalniz glif sinifini kullanir; bos/uyumsuz degerde her idle
// mesaji icin gorunur bir saglik ikonu saglar.
export function normalizeIdleIcon(value) {
  const iconClasses = String(value || '')
    .split(/\s+/)
    .filter((item) => /^fa-[a-z0-9-]+$/i.test(item));
  return iconClasses.at(-1) || 'fa-heart-pulse';
}
