import { writable } from 'svelte/store';

// Kiosk akış modu — Akış A/B/C arasındaki global durum.
export const mode = writable('idle');
