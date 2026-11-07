module.exports = [
"[externals]/crypto [external] (crypto, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("crypto", () => require("crypto"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/@opentelemetry/api [external] (next/dist/compiled/@opentelemetry/api, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/compiled/@opentelemetry/api", () => require("next/dist/compiled/@opentelemetry/api"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/action-async-storage.external.js [external] (next/dist/server/app-render/action-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/server/app-render/action-async-storage.external.js", () => require("next/dist/server/app-render/action-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/after-task-async-storage.external.js [external] (next/dist/server/app-render/after-task-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/server/app-render/after-task-async-storage.external.js", () => require("next/dist/server/app-render/after-task-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/runtime-reacts.external.js [external] (next/dist/server/runtime-reacts.external.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/server/runtime-reacts.external.js", () => require("next/dist/server/runtime-reacts.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[externals]/node:stream [external] (node:stream, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("node:stream", () => require("node:stream"));

module.exports = mod;
}),
"[externals]/path [external] (path, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("path", () => require("path"));

module.exports = mod;
}),
"[project]/src/app/api/preview/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "GET",
    ()=>GET
]);
/**
 * Önizleme girişi (CONTRACT §7).
 *
 *   GET /api/preview?tur=sayfa|blog&slug=<slug>&token=<imzalı token>
 *
 * Token backend preview ucunda doğrulanır; geçerliyse draft mode açılır, token httpOnly
 * `eisa_preview` çerezine yazılır ve ilgili sayfaya yönlendirilir. Yönlendirme hedefi
 * yalnızca doğrulanmış slug'dan üretilir (open redirect yok).
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/headers.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$api$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/next/dist/api/navigation.react-server.js [app-route] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/components/navigation.react-server.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/env.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$utils$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/utils.ts [app-route] (ecmascript)");
;
;
;
;
;
function hata(mesaj, durum) {
    return new Response(mesaj, {
        status: durum,
        headers: {
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "no-store"
        }
    });
}
async function GET(istek) {
    const p = istek.nextUrl.searchParams;
    const tur = p.get("tur") ?? "sayfa";
    const slug = p.get("slug") ?? "";
    const token = p.get("token") ?? "";
    if (tur !== "sayfa" && tur !== "blog" || !__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["SLUG_DESENI"].test(slug) || !token) {
        return hata("Geçersiz önizleme isteği.", 400);
    }
    const gecerli = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["onizlemeTokeniDogrula"])(tur, slug, token);
    if (!gecerli) {
        return hata("Önizleme bağlantısı geçersiz veya süresi dolmuş. Portaldan yeniden önizleme açın.", 401);
    }
    (await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["draftMode"])()).enable();
    (await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["cookies"])()).set(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ONIZLEME_CEREZI"], token, {
        httpOnly: true,
        secure: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].siteUrl.startsWith("https://"),
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60
    });
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["redirect"])(tur === "blog" ? `/blog/${slug}` : (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$utils$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["slugYolu"])(slug));
}
}),
"[project]/src/lib/api.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ApiHatasi",
    ()=>ApiHatasi,
    "ONIZLEME_CEREZI",
    ()=>ONIZLEME_CEREZI,
    "REVALIDATE",
    ()=>REVALIDATE,
    "SLUG_DESENI",
    ()=>SLUG_DESENI,
    "TAG",
    ()=>TAG,
    "getBlogListe",
    ()=>getBlogListe,
    "getBlogYazisi",
    ()=>getBlogYazisi,
    "getSayfa",
    ()=>getSayfa,
    "getSayfaListesi",
    ()=>getSayfaListesi,
    "getSite",
    ()=>getSite,
    "getSonYazilar",
    ()=>getSonYazilar,
    "mediaUrl",
    ()=>mediaUrl,
    "ogGorselleri",
    ()=>ogGorselleri,
    "onizlemeAcikMi",
    ()=>onizlemeAcikMi,
    "onizlemeTokeniDogrula",
    ()=>onizlemeTokeniDogrula,
    "siteUrl",
    ()=>siteUrl
]);
/**
 * e-isa site — sunucu tarafı veri katmanı (CONTRACT §3, §4, §6, §7).
 *
 * Kurallar:
 * - Tüm istekler `API_INTERNAL_URL` üzerinden, sunucuda yapılır (tarayıcıdan API'ye istek gitmez).
 * - Önbellek: klasik `fetch(..., { next: { tags, revalidate } })` modeli (cacheComponents KAPALI).
 *   Tag'ler CONTRACT §6: `site`, `sayfalar`, `sayfa:<slug>`, `blog`, `blog:<slug>`.
 *   Süreler: sayfa/site 3600 sn, blog listesi 300 sn (zamanlanmış yazılar için).
 * - Draft mode açıksa sayfa/blog detayı preview uçlarından `cache: 'no-store'` ile okunur;
 *   token httpOnly `eisa_preview` çerezindedir.
 * - Dayanıklılık:
 *     getSite()          → hata olursa seed içerikli yedek veri döner (site asla çökmez).
 *     getSayfa()/getBlogYazisi() → 404 ise `null` (çağıran notFound() yapar); ağ/5xx hatasında
 *                          `ApiHatasi` fırlatır → error.tsx; ISR son başarılı sürümü sunmaya devam eder.
 *     getSayfaListesi()/getBlogListe() → hata fırlatır; generateStaticParams/sitemap yakalar.
 *     getSonYazilar()    → hata olursa [] döner (blok kendini gizler).
 * - MOCK_API=1 iken hiçbir ağ isteği yapılmaz; src/lib/mock fixture'ları döner.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/rsc/react.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/headers.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$api$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/next/dist/api/navigation.react-server.js [app-route] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/components/navigation.react-server.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/env.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$media$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/media.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/src/lib/mock/index.ts [app-route] (ecmascript) <locals>");
;
;
;
;
;
;
;
const ONIZLEME_CEREZI = "eisa_preview";
const REVALIDATE = {
    site: 3600,
    sayfa: 3600,
    sayfaListesi: 3600,
    blogListe: 300,
    blogDetay: 3600
};
const TAG = {
    site: "site",
    sayfalar: "sayfalar",
    sayfa: (slug)=>`sayfa:${slug}`,
    blog: "blog",
    blogYazisi: (slug)=>`blog:${slug}`
};
const SLUG_DESENI = /^[a-z0-9-]+$/;
const PUBLIC = "/api/website/public";
const PREVIEW = "/api/website/preview";
const ISTEK_ZAMAN_ASIMI_MS = 8000;
class ApiHatasi extends Error {
    /** HTTP durumu; ağ hatasında `null`. */ durum;
    yol;
    constructor(mesaj, durum, yol){
        super(mesaj);
        this.name = "ApiHatasi";
        this.durum = durum;
        this.yol = yol;
    }
}
/**
 * API'ye GET isteği. 404 ve 403 `veri: null` ile döner; diğer hatalar `ApiHatasi` fırlatır.
 * `yol` sorgu dizgesi dahil, `/api/...` ile başlar.
 */ async function apiGet(yol, secenekler = {}) {
    const url = `${__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].apiInternalUrl}${yol}`;
    let yanit;
    try {
        yanit = await fetch(url, {
            // App-key: public/önizleme uçları yalnızca site sunucusuna açıktır (yoksa API 404 döner).
            headers: {
                Accept: "application/json",
                "X-Website-Token": __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].websiteServerToken
            },
            signal: AbortSignal.timeout(ISTEK_ZAMAN_ASIMI_MS),
            ...secenekler.noStore ? {
                cache: "no-store"
            } : {
                next: {
                    tags: secenekler.tags,
                    revalidate: secenekler.revalidate
                }
            }
        });
    } catch (hata) {
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["unstable_rethrow"])(hata);
        const neden = hata instanceof Error ? hata.message : String(hata);
        throw new ApiHatasi(`API'ye ulaşılamadı (${yol}): ${neden}`, null, yol);
    }
    if (yanit.status === 404 || yanit.status === 403) {
        return {
            durum: yanit.status,
            veri: null
        };
    }
    if (!yanit.ok) {
        throw new ApiHatasi(`API hatası ${yanit.status} (${yol})`, yanit.status, yol);
    }
    try {
        return {
            durum: yanit.status,
            veri: await yanit.json()
        };
    } catch  {
        throw new ApiHatasi(`API geçersiz JSON döndürdü (${yol})`, yanit.status, yol);
    }
}
/** Hata kaydı — sunucu loglarında tek biçim. */ function logla(baglam, hata) {
    const mesaj = hata instanceof Error ? hata.message : String(hata);
    console.error(`[e-isa api] ${baglam}: ${mesaj}`);
}
async function onizlemeAcikMi() {
    try {
        return (await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["draftMode"])()).isEnabled;
    } catch (hata) {
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["unstable_rethrow"])(hata);
        return false;
    }
}
/** Draft mode açıksa `eisa_preview` çerezindeki token; değilse null. */ async function onizlemeTokeni() {
    if (!await onizlemeAcikMi()) return null;
    try {
        return (await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["cookies"])()).get(ONIZLEME_CEREZI)?.value ?? null;
    } catch (hata) {
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["unstable_rethrow"])(hata);
        return null;
    }
}
async function onizlemeTokeniDogrula(tur, slug, token) {
    if (!SLUG_DESENI.test(slug) || !token) return false;
    if (__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].mockApi) return tur === "sayfa" ? (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockSayfaGetir"])(slug) !== null : (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockBlogYazisi"])(slug) !== null;
    const yol = tur === "sayfa" ? `${PREVIEW}/sayfalar/${slug}/?token=${encodeURIComponent(token)}` : `${PREVIEW}/blog/${slug}/?token=${encodeURIComponent(token)}`;
    try {
        const r = await apiGet(yol, {
            noStore: true
        });
        return r.durum >= 200 && r.durum < 300;
    } catch (hata) {
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["unstable_rethrow"])(hata);
        logla("önizleme doğrulama", hata);
        return false;
    }
}
const getSite = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["cache"])(async ()=>{
    if (__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].mockApi) return (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockSiteGetir"])();
    try {
        const r = await apiGet(`${PUBLIC}/site/`, {
            tags: [
                TAG.site
            ],
            revalidate: REVALIDATE.site
        });
        if (r.veri) return r.veri;
        logla("site", new Error(`beklenmeyen durum ${r.durum}`));
    } catch (hata) {
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["unstable_rethrow"])(hata);
        logla("site (yedek veri kullanılıyor)", hata);
    }
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockSiteGetir"])();
});
async function getSayfaListesi() {
    if (__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].mockApi) return (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockSayfaListesi"])();
    const r = await apiGet(`${PUBLIC}/sayfalar/`, {
        tags: [
            TAG.sayfalar
        ],
        revalidate: REVALIDATE.sayfaListesi
    });
    return r.veri ?? [];
}
const getSayfa = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["cache"])(async (slug)=>{
    if (!SLUG_DESENI.test(slug)) return null;
    if (__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].mockApi) return (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockSayfaGetir"])(slug);
    const token = await onizlemeTokeni();
    if (token) {
        const r = await apiGet(`${PREVIEW}/sayfalar/${slug}/?token=${encodeURIComponent(token)}`, {
            noStore: true
        });
        if (r.durum !== 403) return r.veri;
        console.warn(`[e-isa api] önizleme token'ı geçersiz/süresi dolmuş (sayfa:${slug}); yayındaki sürüm gösteriliyor.`);
    }
    const r = await apiGet(`${PUBLIC}/sayfalar/${slug}/`, {
        tags: [
            TAG.sayfa(slug)
        ],
        revalidate: REVALIDATE.sayfa
    });
    return r.veri;
});
const getBlogListe = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["cache"])(async (params = {})=>{
    const kategori = params.kategori && SLUG_DESENI.test(params.kategori) ? params.kategori : undefined;
    const sayfa = Math.max(1, Math.floor(params.sayfa ?? 1));
    const boyut = Math.min(Math.max(1, Math.floor(params.boyut ?? 9)), 24);
    if (__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].mockApi) return (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockBlogListe"])({
        kategori,
        sayfa,
        boyut
    });
    const qs = new URLSearchParams();
    if (kategori) qs.set("kategori", kategori);
    qs.set("sayfa", String(sayfa));
    qs.set("boyut", String(boyut));
    const r = await apiGet(`${PUBLIC}/blog/?${qs.toString()}`, {
        tags: [
            TAG.blog
        ],
        revalidate: REVALIDATE.blogListe
    });
    // Geçersiz sayfa numarası vb. durumlarda backend 404 dönebilir: boş liste.
    return r.veri ?? {
        sonuclar: [],
        toplam: 0,
        sayfa,
        sayfa_sayisi: 1,
        kategoriler: []
    };
});
async function getSonYazilar(adet = 3, kategori) {
    try {
        const liste = await getBlogListe({
            boyut: Math.min(Math.max(adet, 1), 6),
            kategori: kategori || undefined
        });
        return liste.sonuclar;
    } catch (hata) {
        (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$components$2f$navigation$2e$react$2d$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["unstable_rethrow"])(hata);
        logla("son yazılar", hata);
        return [];
    }
}
const getBlogYazisi = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["cache"])(async (slug)=>{
    if (!SLUG_DESENI.test(slug)) return null;
    if (__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].mockApi) return (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$index$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$locals$3e$__["mockBlogYazisi"])(slug);
    const token = await onizlemeTokeni();
    if (token) {
        const r = await apiGet(`${PREVIEW}/blog/${slug}/?token=${encodeURIComponent(token)}`, {
            noStore: true
        });
        if (r.durum !== 403) return r.veri;
        console.warn(`[e-isa api] önizleme token'ı geçersiz/süresi dolmuş (blog:${slug}); yayındaki sürüm gösteriliyor.`);
    }
    const r = await apiGet(`${PUBLIC}/blog/${slug}/`, {
        tags: [
            TAG.blog,
            TAG.blogYazisi(slug)
        ],
        revalidate: REVALIDATE.blogDetay
    });
    return r.veri;
});
function mediaUrl(yol) {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$media$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mediaUrlOlustur"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].mediaBaseUrl, yol);
}
function siteUrl(yol = "/") {
    return `${__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].siteUrl}${yol.startsWith("/") ? "" : "/"}${yol}`;
}
function ogGorselleri(medya, ayarlar, alt) {
    const m = medya ?? ayarlar.og_gorsel;
    const url = m ? mediaUrl(m.yol) : null;
    if (m && url) {
        return [
            {
                url,
                width: m.genislik ?? undefined,
                height: m.yukseklik ?? undefined,
                alt: m.alt || alt
            }
        ];
    }
    return [
        {
            url: "/opengraph-image",
            width: 1200,
            height: 630,
            alt
        }
    ];
}
}),
"[project]/src/lib/env.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "env",
    ()=>env
]);
;
/**
 * Sunucu tarafı ortam değişkenleri (CONTRACT §1). Hepsinin lokal varsayılanı vardır.
 * İstemci bileşenlerinde KULLANMAYIN — istemciye gereken değerler (ör. medya tabanı)
 * layout'ta `SiteProvider` ile prop olarak aktarılır.
 */ function sonEgikCizgisiz(deger) {
    return deger.replace(/\/+$/, "");
}
function bayrak(deger) {
    return deger === "1" || deger?.toLowerCase() === "true";
}
const env = {
    /** Sunucu tarafı fetch tabanı (K8s'te cluster içi servis adresi). */ apiInternalUrl: sonEgikCizgisiz(process.env.API_INTERNAL_URL || "http://localhost:8000"),
    /** Medya `yol` alanının önüne eklenir (prod: https://api.eisa.com.tr). */ mediaBaseUrl: sonEgikCizgisiz(process.env.MEDIA_BASE_URL || "http://localhost:8000"),
    /** Canonical, sitemap, OG için (prod: https://eisa.com.tr). */ siteUrl: sonEgikCizgisiz(process.env.SITE_URL || "http://localhost:3000"),
    /** Backend → site revalidate webhook'u için ortak sır. */ revalidateSecret: process.env.REVALIDATE_SECRET || "dev-revalidate-secret",
    /** Site sunucusunun API'ye "ben siteyim" demesi için (X-Website-Token). */ websiteServerToken: process.env.WEBSITE_SERVER_TOKEN || "dev-website-token",
    /** MOCK_API=1 iken API yerine src/lib/mock fixture'ları kullanılır. */ mockApi: bayrak(process.env.MOCK_API)
};
}),
"[project]/src/lib/media.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/**
 * Medya URL yardımcıları — hem sunucu hem istemci tarafında güvenle kullanılabilir (env okumaz).
 * Sunucuda `mediaUrl()` (lib/api.ts), istemcide `useMediaUrl()` (components/SiteProvider.tsx) kullanın.
 */ __turbopack_context__.s([
    "mediaUrlOlustur",
    ()=>mediaUrlOlustur,
    "medyaVarMi",
    ()=>medyaVarMi
]);
function mediaUrlOlustur(taban, yol) {
    if (!yol) return null;
    if (/^https?:\/\//i.test(yol)) return yol;
    const t = taban.replace(/\/+$/, "");
    return `${t}${yol.startsWith("/") ? "" : "/"}${yol}`;
}
function medyaVarMi(m) {
    return Boolean(m && m.yol);
}
}),
"[project]/src/lib/mock/blog.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/**
 * MOCK: blog — CONTRACT §9: 3 kategori, 3 yayınlanmış yazı (temkinli dil).
 */ __turbopack_context__.s([
    "mockBlogYazilari",
    ()=>mockBlogYazilari,
    "mockKategoriler",
    ()=>mockKategoriler,
    "ozetle",
    ()=>ozetle
]);
const mockKategoriler = [
    {
        ad: "Sağlık Okuryazarlığı",
        slug: "saglik-okuryazarligi"
    },
    {
        ad: "Eczane Yönetimi",
        slug: "eczane-yonetimi"
    },
    {
        ad: "Duyurular",
        slug: "duyurular"
    }
];
const [saglik, eczane, duyuru] = mockKategoriler;
const YAZAR = "e-isa Ekibi";
const mockBlogYazilari = [
    {
        slug: "pilot-sureci-nasil-isler",
        baslik: "e-isa 1 aylık ücretsiz pilot süreci nasıl işler?",
        ozet: "Başvurudan kuruluma, veri takibinden değerlendirme toplantısına kadar 30 günlük ücretsiz pilot sürecin adımlarını özetledik.",
        kapak: null,
        kategori: duyuru,
        etiketler: [
            "pilot",
            "kurulum",
            "e-isa"
        ],
        yazar_adi: YAZAR,
        yayin_tarihi: "2026-11-05T09:00:00Z",
        okuma_suresi: 4,
        seo: {
            baslik: "1 Aylık Ücretsiz Pilot Süreci Nasıl İşler?",
            aciklama: "e-isa pilot süreci: başvuru, kurulum, eğitim, izleme ve değerlendirme adımları.",
            og_gorsel: null
        },
        icerik_html: `
<p>e-isa'yı eczanenizde denemek için herhangi bir ücret ödemeniz veya uzun vadeli bir taahhüde girmeniz gerekmez. Pilot sürecin amacı basit: e-isa'yı varsayımlarla değil, eczanenizin kendi verileriyle değerlendirmenizi sağlamak.</p>
<h2>1. Başvuru ve ön görüşme</h2>
<p>Sitemizdeki pilot başvuru formunu doldurduktan sonra ekibimiz sizinle iletişime geçer. Kısa bir ön görüşmede eczanenizin müşteri akışını, bekleme alanını ve beklentilerinizi konuşuruz.</p>
<h2>2. Kurulum</h2>
<p>Kompakt kiosk ünitesini bekleme alanında en uygun konuma yerleştiririz. Kurulum genellikle eczanenin günlük işleyişini aksatmadan, kısa sürede tamamlanır.</p>
<h2>3. Kısa eğitim</h2>
<p>Eczane ekibine QR / fiş akışını ve sonuçların nasıl değerlendirileceğini anlatırız. e-isa'nın ürettiği çıktı bir <strong>ön inceleme</strong>dir; son değerlendirme her zaman eczacıdadır.</p>
<h2>4. İzleme ve geri bildirim</h2>
<p>30 gün boyunca etkileşim sayısı, kategori dağılımı ve danışmanlık sürecine etkisi gibi göstergeleri birlikte izleriz. Saha ekibimiz süreç boyunca yanınızdadır.</p>
<h2>5. Değerlendirme</h2>
<p>Pilot sonunda verileri birlikte değerlendiririz. Devam edip etmeme kararı tamamen sizindir.</p>
<blockquote>Pilot süreçte paylaşılan rakamlar eczaneye özgüdür; başka eczaneler için garanti veya taahhüt niteliği taşımaz.</blockquote>
`.trim(),
        ilgili: []
    },
    {
        slug: "durtme-yaklasimi-saglik-okuryazarligi",
        baslik: "Dürtme (nudge) yaklaşımı sağlık okuryazarlığına nasıl katkı sağlar?",
        ozet: "Davranışsal ekonomiden doğan dürtme yaklaşımı, kişiyi yönlendirmeden düşünmeye davet eder. Eczane ortamında bunun ne anlama geldiğine baktık.",
        kapak: null,
        kategori: saglik,
        etiketler: [
            "dürtme",
            "nudge",
            "sağlık okuryazarlığı"
        ],
        yazar_adi: YAZAR,
        yayin_tarihi: "2026-10-28T09:00:00Z",
        okuma_suresi: 5,
        seo: {
            baslik: "Dürtme (Nudge) Yaklaşımı ve Sağlık Okuryazarlığı",
            aciklama: "Dürtme yaklaşımının eczane ortamında sağlık okuryazarlığına olası katkıları ve sınırları.",
            og_gorsel: null
        },
        icerik_html: `
<p>Dürtme (nudge), davranışsal ekonomide kişinin seçim özgürlüğünü kısıtlamadan, karar ortamını sadeleştirerek daha bilinçli seçimler yapmasını kolaylaştıran yaklaşımların genel adıdır. Yasaklamaz, zorlamaz; yalnızca düşünmeye alan açar.</p>
<h2>Sağlık okuryazarlığı neden önemli?</h2>
<p>Sağlık okuryazarlığı, kişinin sağlıkla ilgili bilgiye ulaşma, onu anlama ve bu bilgiyle uygun sorular sorabilme becerisidir. Eczacısına doğru soruyu soran kişi, görüşmeden daha fazla fayda sağlar.</p>
<h2>Eczane ortamında dürtme ne demek?</h2>
<p>Reçete hazırlanırken geçen birkaç dakika, kişinin kendi ihtiyaçlarını düşünmesi için uygun bir andır. e-isa bu anda:</p>
<ul>
<li>karmaşık tıbbi terimler yerine yalın seçenekler sunar,</li>
<li>enerji, uyku, sindirim gibi gündelik başlıklarda kısa sorular sorar,</li>
<li>sonucu bir <strong>kategori</strong> olarak özetler ve eczacıya iletir.</li>
</ul>
<h2>Sınırları net çizmek</h2>
<p>Dürtme yaklaşımı bir teşhis aracı değildir ve tedavi önermez. e-isa da marka önermez; yalnızca eczacıyla yapılacak görüşmeye hazırlık niteliğinde bir kategori özeti üretir. Hangi ürünün kişiye uygun olduğuna, gerekiyorsa hekime yönlendirme yapılıp yapılmayacağına eczacı karar verir.</p>
<h2>Sonuç</h2>
<p>Doğru tasarlanmış küçük bir dijital etkileşim, kişinin eczacısıyla daha odaklı bir görüşme yapmasına yardımcı olabilir. Amaç satış baskısı değil, farkındalıktır.</p>
`.trim(),
        ilgili: []
    },
    {
        slug: "recete-bekleme-suresi-firsat",
        baslik: "Reçete bekleme süresi eczane için neden bir fırsat?",
        ozet: "Reçete hazırlanırken geçen kısa bekleme süresi, doğru kurgulandığında hem müşteri deneyimi hem de eczacının danışmanlık rolü için değerli bir ana dönüşebilir.",
        kapak: null,
        kategori: eczane,
        etiketler: [
            "eczane yönetimi",
            "müşteri deneyimi"
        ],
        yazar_adi: YAZAR,
        yayin_tarihi: "2026-10-20T09:00:00Z",
        okuma_suresi: 4,
        seo: {
            baslik: "Reçete Bekleme Süresi Eczane İçin Neden Bir Fırsat?",
            aciklama: "Eczanedeki bekleme süresini müşteri deneyimi ve danışmanlık açısından değerlendirmenin yolları.",
            og_gorsel: null
        },
        icerik_html: `
<p>Eczaneye gelen pek çok kişi, reçetesi hazırlanırken birkaç dakika bekler. Bu süre çoğu zaman telefona bakarak ya da sırayı izleyerek geçer. Oysa bekleme anı, doğru kurgulandığında hem müşteri hem de eczane için anlamlı bir fırsattır.</p>
<h2>Sessiz müşteri</h2>
<p>Birçok kişi, eczacısına sormak istediği bir konuyu yoğunluk veya çekingenlik nedeniyle dile getirmez. Bekleme süresinde sunulan sade bir dijital etkileşim, bu kişilerin ihtiyaçlarını fark etmelerine ve görüşmeye hazırlıklı gelmelerine yardımcı olabilir.</p>
<h2>Eczacının danışmanlık rolü</h2>
<p>Kişi kendi ihtiyacını önceden düşündüğünde, eczacıyla yapılan görüşme daha kısa ve daha odaklı olabilir. Eczacı, bir kategori özetiyle başlayan görüşmede uzmanlığını daha etkin kullanır.</p>
<h2>Tamamlayıcı kategoriler</h2>
<p>Kısa sorulara verilen yanıtlar, yalnızca tek bir ihtiyaca değil, tamamlayıcı kategorilere de işaret edebilir. Bu da eczacının bütüncül bir danışmanlık sunmasını kolaylaştırır.</p>
<h2>Dikkat edilmesi gerekenler</h2>
<ul>
<li>Etkileşim kısa ve gönüllü olmalıdır.</li>
<li>Marka yönlendirmesi yapılmamalı, yalnızca kategori düzeyinde kalınmalıdır.</li>
<li>Son değerlendirme her zaman eczacıya bırakılmalıdır.</li>
</ul>
<p>Sepet ortalamasındaki olası değişim eczaneden eczaneye farklılık gösterir; bu nedenle en sağlıklı yöntem, kendi verilerinizle yapılan bir pilot değerlendirmedir.</p>
`.trim(),
        ilgili: []
    }
];
function ozetle(y) {
    return {
        slug: y.slug,
        baslik: y.baslik,
        ozet: y.ozet,
        kapak: y.kapak,
        kategori: y.kategori,
        etiketler: y.etiketler,
        yazar_adi: y.yazar_adi,
        yayin_tarihi: y.yayin_tarihi,
        okuma_suresi: y.okuma_suresi
    };
}
}),
"[project]/src/lib/mock/index.ts [app-route] (ecmascript) <locals>", ((__turbopack_context__) => {
"use strict";

/**
 * MOCK API — `MOCK_API=1` iken lib/api.ts bu fonksiyonları kullanır.
 * Yanıt biçimleri CONTRACT §3 ile birebir aynıdır.
 */ __turbopack_context__.s([
    "mockBlogListe",
    ()=>mockBlogListe,
    "mockBlogYazisi",
    ()=>mockBlogYazisi,
    "mockSayfaGetir",
    ()=>mockSayfaGetir,
    "mockSayfaListesi",
    ()=>mockSayfaListesi,
    "mockSiteGetir",
    ()=>mockSiteGetir
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$blog$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/mock/blog.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$sayfalar$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/mock/sayfalar.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$site$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/mock/site.ts [app-route] (ecmascript)");
;
;
;
;
/** Derin kopya — çağıran tarafın fixture'ı değiştirmesini engeller. */ function kopya(v) {
    return structuredClone(v);
}
function mockSiteGetir() {
    return kopya(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$site$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mockSite"]);
}
function mockSayfaListesi() {
    return Object.values(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$sayfalar$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mockSayfalar"]).map((s)=>({
            slug: s.slug,
            guncellenme: s.yayin_tarihi ?? "2026-11-07T10:00:00Z"
        }));
}
function mockSayfaGetir(slug) {
    const s = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$sayfalar$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mockSayfalar"][slug];
    return s ? kopya(s) : null;
}
function mockBlogListe(params) {
    const boyut = Math.min(Math.max(params.boyut ?? 9, 1), 24);
    const sirali = [
        ...__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$blog$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mockBlogYazilari"]
    ].sort((a, b)=>b.yayin_tarihi.localeCompare(a.yayin_tarihi));
    const filtreli = params.kategori ? sirali.filter((y)=>y.kategori?.slug === params.kategori) : sirali;
    const sayfaSayisi = Math.max(1, Math.ceil(filtreli.length / boyut));
    const sayfa = Math.min(Math.max(params.sayfa ?? 1, 1), sayfaSayisi);
    const bas = (sayfa - 1) * boyut;
    return {
        sonuclar: filtreli.slice(bas, bas + boyut).map(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$blog$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ozetle"]),
        toplam: filtreli.length,
        sayfa,
        sayfa_sayisi: sayfaSayisi,
        kategoriler: kopya(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$blog$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mockKategoriler"])
    };
}
function mockBlogYazisi(slug) {
    const y = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$blog$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mockBlogYazilari"].find((x)=>x.slug === slug);
    if (!y) return null;
    const ilgili = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$blog$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["mockBlogYazilari"].filter((x)=>x.slug !== slug && x.kategori?.slug && x.kategori.slug === y.kategori?.slug).slice(0, 3).map(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$blog$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["ozetle"]);
    return {
        ...kopya(y),
        ilgili
    };
}
}),
"[project]/src/lib/mock/sayfalar.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/**
 * MOCK: `GET /api/website/public/sayfalar/<slug>/` — CONTRACT §9 seed planına göre.
 * 16 blok tipinin her biri en az bir sayfada geçer (blok ajanları bu fixture'larla geliştirir).
 *
 * İçerik tonu: e-isa teşhis/tedavi sistemi değildir; marka değil kategori önerir;
 * kazanç rakamları örnek senaryodur; son değerlendirme eczacıdadır.
 */ __turbopack_context__.s([
    "mockSayfalar",
    ()=>mockSayfalar
]);
const YAYIN = "2026-11-07T10:00:00Z";
function blok(id, tip, anchor_id, veri) {
    return {
        id,
        tip,
        anchor_id,
        veri
    };
}
/* ------------------------------------------------------------------ */ /* anasayfa                                                            */ /* ------------------------------------------------------------------ */ const anasayfa = {
    slug: "anasayfa",
    baslik: "Anasayfa",
    seo: {
        baslik: "Eczaneler için Yapay Zeka Destekli Karar Destek Ekosistemi",
        aciklama: "e-isa, eczanelerde reçete bekleme süresini yapay zeka destekli sağlık okuryazarlığı ve eczacı kontrollü danışmanlık deneyimine dönüştüren modern kiosk ekosistemidir.",
        og_gorsel: null
    },
    yayin_tarihi: YAYIN,
    revizyon_id: 1,
    bloklar: [
        blok("b_1", "hero", "", {
            rozet: "Eczacının Ön Hazırlık Asistanı",
            baslik: "Eczanenizdeki Reçete Bekleme Süresini Kategori Bazlı Sağlık Okuryazarlığına Dönüştürün",
            vurgu: "Sağlık Okuryazarlığına Dönüştürün",
            alt_metin: "e-isa, yaşam tarzına ve beyan edilen ihtiyaçlara uygun kategorik sağlık okuryazarlığı rehberliği sunar; eczacının ön hazırlık rolünü merkeze alan güvenli bir dijital deneyim sağlar.",
            vurgu_kartlari: [
                {
                    ikon: "ClockCounterClockwise",
                    metin: "60 saniyede kategorik ön hazırlık"
                },
                {
                    ikon: "Package",
                    metin: "Marka değil, ihtiyaç kategorisi önerir"
                },
                {
                    ikon: "ShieldCheck",
                    metin: "Son değerlendirme eczacı kontrolündedir"
                },
                {
                    ikon: "CheckCircle",
                    metin: "1 ay ücretsiz pilot süreç"
                }
            ],
            butonlar: [
                {
                    etiket: "Pilot Süreci İncele",
                    href: "/#pilot",
                    stil: "birincil"
                },
                {
                    etiket: "Nasıl Çalışır?",
                    href: "/#nasil-calisir",
                    stil: "ikincil"
                }
            ],
            kiosk_animasyonu: true
        }),
        blok("b_2", "ozellik_kartlari", "nasil-calisir", {
            ust_baslik: "e-isa nedir?",
            baslik: "Eczacının Ön Hazırlık Asistanı",
            aciklama: "e-isa; eczane içinde bekleyen kişinin yaşam kalitesini etkileyebilecek yorgunluk, stres, sindirim düzeni, bağışıklık desteği, enerji ve uyku gibi başlıklarda kısa ve sade bir dijital etkileşim yaşamasını sağlar.",
            sutun: 4,
            kartlar: [
                {
                    ikon: "Brain",
                    baslik: "Kısa Dijital Etkileşim",
                    metin: "Yalın sorularla kişiyi karmaşık tıbbi terimlerle yormadan ihtiyacını düşünmeye yönlendirir."
                },
                {
                    ikon: "Package",
                    baslik: "Kategori Bazlı Öneri",
                    metin: "Verilen yanıtları kategori mantığıyla değerlendirir ve eczacıya ön inceleme olarak sunar."
                },
                {
                    ikon: "ShieldCheck",
                    baslik: "Eczacı Onayı",
                    metin: "Sistemin ürettiği ön inceleme eczacının mesleki onayına sunulur; son değerlendirme eczacıdadır."
                },
                {
                    ikon: "QrCode",
                    baslik: "QR / Fiş Aktarımı",
                    metin: "Dijital sonuç QR kod veya fiş ile hızlıca eczacıya iletilir."
                }
            ],
            arka_plan: "gri"
        }),
        blok("b_3", "vurgu_bandi", "", {
            ikon: "Sparkle",
            baslik: "Ön Hazırlıktan Sonra Farkındalık: Dürtme (Nudge) Yaklaşımı",
            metin: "e-isa, davranışsal ekonomiden ilham alan dürtme (nudge) yaklaşımını sağlık okuryazarlığı alanına taşır. Kişiyi karmaşık tıbbi terimlerle yormadan yalın seçenekler üzerinden sağlık ihtiyacını düşünmeye yönlendirir. Bekleme süresinde oluşan bu kısa dijital deneyim, eczacıyla daha bilinçli ve odaklı bir görüşme yapılmasına yardımcı olur.",
            vurgu_cumlesi: "Ön hazırlık iklimini e-isa hazırlar, profesyonel son dokunuşu eczacı yapar.",
            stil: "kirmizi"
        }),
        blok("b_4", "ozellik_kartlari", "eczaci-kontrolu", {
            ust_baslik: "Eczacı için 3 öncelik",
            baslik: "Kontrol Her Zaman Sizde",
            aciklama: "e-isa bir satış terminali değil; eczacının uzmanlığını destekleyen bir ön hazırlık katmanıdır.",
            sutun: 3,
            kartlar: [
                {
                    ikon: "Package",
                    baslik: "Asla Marka Önermez",
                    metin: "e-isa, spesifik marka dayatmaz. Yalnızca ihtiyaca yönelik kategori önerir. Hangi ürünün kişiye daha uygun olduğuna karar veren yetkili her zaman eczacıdır."
                },
                {
                    ikon: "UserCircle",
                    baslik: "Süreci Eczacı Tamamlar",
                    metin: "Kiosk bir satış terminali değil, kişiyi görüşmeye hazırlayan dijital bir köprüdür. Son karar, banko başında eczacının uzmanlığıyla verilir."
                },
                {
                    ikon: "CheckCircle",
                    baslik: "Stokla Uyumlu Çalışır",
                    metin: "Sistem, eczanenin mevcut ürün portföyünü destekleyecek rasyonel kategori argümanları üretir. Böylece stok yönetimi ve danışmanlık daha verimli hale gelebilir."
                }
            ],
            arka_plan: "acik"
        }),
        blok("b_5", "scroll_hikaye", "yolculuk", {
            ust_baslik: "Müşterinin eczane içi yolculuğu",
            baslik: "Beklemeden Etkileşime: 4 Adımlı Yolculuk",
            aciklama: "Reçete teslim edildiği andan eczacıyla görüşmeye kadar geçen süre, kısa ve anlamlı bir hazırlığa dönüşür.",
            adimlar: [
                {
                    baslik: "Reçete Teslimi",
                    metin: "Reçete teslim edilir ve bekleme süresi başlar.",
                    ekran_baslik: "Hoş geldiniz",
                    ekran_metin: "Beklerken kısa bir sağlık okuryazarlığı turuna ne dersiniz?"
                },
                {
                    baslik: "Dijital Etkileşim",
                    metin: "Müşteri e-isa ekranındaki sade arayüzle etkileşime girer.",
                    ekran_baslik: "Son zamanlarda en çok neye dikkat ediyorsunuz?",
                    ekran_metin: "Enerji · Uyku · Sindirim · Bağışıklık"
                },
                {
                    baslik: "Kategori Önerisi",
                    metin: "2-4 kısa soruyla kişiselleştirilmiş bir kategori önerisi oluşturulur.",
                    ekran_baslik: "Önerilen kategori",
                    ekran_metin: "Enerji ve yorgunluk desteği — marka değil, ihtiyaç kategorisi."
                },
                {
                    baslik: "Eczacı Onayı",
                    metin: "QR/fiş eczacıya iletilir; eczacı öneriyi uzmanlığıyla değerlendirir.",
                    ekran_baslik: "QR kodunuz hazır",
                    ekran_metin: "Son değerlendirme eczacınızdadır."
                }
            ]
        }),
        blok("b_6", "kazanc_hesaplayici", "kazanc", {
            ust_baslik: "Kazanç modeli",
            baslik: "Sepet Büyüten Zeka: Cross-Sell Etkisi",
            aciklama: "e-isa, müşterinin yanıtlarına göre yalnızca tek bir ürün kategorisine değil, tamamlayıcı kategori fırsatlarına da dikkat çeker. Bu yapı, eczacının danışmanlık gücünü artırırken sepet ortalamasını büyütme potansiyeli oluşturur.",
            kademeler: [
                {
                    etkilesim_min: 1,
                    etkilesim_max: 10,
                    gunluk_satis: 1,
                    aylik_satis: 25,
                    aylik_ciro: 18000,
                    aylik_kar: 6000
                },
                {
                    etkilesim_min: 10,
                    etkilesim_max: 20,
                    gunluk_satis: 3,
                    aylik_satis: 75,
                    aylik_ciro: 56000,
                    aylik_kar: 18000
                },
                {
                    etkilesim_min: 20,
                    etkilesim_max: 30,
                    gunluk_satis: 6,
                    aylik_satis: 150,
                    aylik_ciro: 110000,
                    aylik_kar: 36000
                },
                {
                    etkilesim_min: 30,
                    etkilesim_max: 40,
                    gunluk_satis: 10,
                    aylik_satis: 250,
                    aylik_ciro: 185000,
                    aylik_kar: 62000
                },
                {
                    etkilesim_min: 40,
                    etkilesim_max: 50,
                    gunluk_satis: 15,
                    aylik_satis: 375,
                    aylik_ciro: 280000,
                    aylik_kar: 94000
                }
            ],
            varsayilan_etkilesim: 25,
            slider_max: 50,
            para_birimi: "TL",
            uyari_notu: "Bu değerler garanti değildir; örnek potansiyel senaryo olarak sunulmuştur. Gerçek sonuçlar eczanenin konumuna, müşteri profiline ve danışmanlık sürecine göre değişir.",
            tablo_goster: true
        }),
        blok("b_7", "ozellik_kartlari", "", {
            ust_baslik: "Pasif gelir ekosistemi",
            baslik: "e-isa Kendi Kendini Finanse Eden Bir Ekosisteme Dönüşebilir",
            aciklama: "e-isa, kiosk ekranını eczane atmosferine uygun dijital bilgilendirme alanı olarak da değerlendirebilir. İçerik yönetimi ve teknik güncellemeler merkezi olarak yürütülür; eczane operasyonel yük almadan ek katkı potansiyeli elde eder.",
            sutun: 4,
            kartlar: [
                {
                    ikon: "Megaphone",
                    baslik: "Dijital Bilgilendirme",
                    metin: "Ekran, eczane atmosferine uygun bilgilendirici içerikler için paylaşımlı bir alan olarak kullanılabilir."
                },
                {
                    ikon: "Coins",
                    baslik: "%10 Altyapı Katkısı",
                    metin: "Bilgilendirme gelirlerinden altyapı ve lisans maliyetlerine destek olacak bir katkı modeli öngörülür."
                },
                {
                    ikon: "Lightning",
                    baslik: "Operasyonel Yük Yok",
                    metin: "İçerik planlama, yayın ve teknik güncellemeler merkezi olarak yönetilir."
                },
                {
                    ikon: "ShieldCheck",
                    baslik: "Etik İçerik Denetimi",
                    metin: "Yayınlanacak içerikler eczane etiğine ve sağlık beyanı kurallarına uygunluk açısından denetlenir."
                }
            ],
            arka_plan: "gri"
        }),
        blok("b_8", "sss", "sss", {
            ust_baslik: "Sık sorulan sorular",
            baslik: "Merak Ettikleriniz",
            aciklama: "e-isa hakkında eczacıların en sık sorduğu soruları yanıtladık.",
            sorular: [
                {
                    soru: "Kiosk iş yerime sığar mı?",
                    cevap: "Samsung kiosk'un kompakt yapısı, standart bir dergilikten fazla alan kaplamadan eczane ortamına entegre olabilir."
                },
                {
                    soru: "Müşteriler kiosku kullanır mı?",
                    cevap: "Yalın seçenekler, kısa etkileşim süresi ve dikkat çekici arayüz sayesinde müşterinin bekleme anında ekranla etkileşime girmesi hedeflenir.\n\nPilot süreçte etkileşim verilerini birlikte izleyerek eczanenize özgü tabloyu görebilirsiniz."
                },
                {
                    soru: "Biz zaten satış yapıyoruz, neden e-isa?",
                    cevap: "e-isa, ihtiyacını dile getirmeyen sessiz müşteriyi farkındalık sürecine dahil eder ve eczacının danışmanlık sürecini destekler."
                },
                {
                    soru: "İçerikler eczacılık etiğine uygun mu?",
                    cevap: "Yayınlanan içerikler, eczane atmosferine ve ilgili sağlık beyanı kurallarına uygunluk açısından denetlenir. e-isa teşhis koymaz, tedavi önermez ve marka yönlendirmesi yapmaz."
                },
                {
                    soru: "İnternet kesilirse ne olur?",
                    cevap: "Sistem çevrimdışı senkronizasyon mantığıyla çalışır. Bağlantı kesintilerinde veriler cihazda tutulur ve bağlantı geldiğinde yeniden senkronize edilir."
                }
            ],
            arka_plan: "acik"
        }),
        blok("b_9", "blog_son_yazilar", "", {
            baslik: "Blogdan Son Yazılar",
            aciklama: "Sağlık okuryazarlığı, eczane yönetimi ve e-isa'dan haberler.",
            adet: 3
        }),
        blok("b_10", "basvuru_formu", "pilot", {
            ust_baslik: "1 ay ücretsiz",
            baslik: "Pilot Süreç: e-isa Konuşsun, Ön İnceleme Sizde Olsun",
            aciklama: "e-isa'yı varsayımlarla değil, eczanenizin kendi verileriyle değerlendirin. 30 günlük pilot süreçte etkileşimi, danışmanlık sürecini ve sepet ortalamasındaki değişimi birlikte gözlemleyelim.",
            form_tipi: "pilot",
            maddeler: [
                {
                    ikon: "Storefront",
                    baslik: "Kompakt Pilot Ünite",
                    metin: "Pratik test için hazır kurulum."
                },
                {
                    ikon: "Handshake",
                    baslik: "Yakın Saha Desteği",
                    metin: "Pilot süresince profesyonel destek."
                },
                {
                    ikon: "Target",
                    baslik: "Stratejik Danışmanlık",
                    metin: "Kalıcı süreçte düzenli ziyaret ve değerlendirme."
                }
            ],
            basari_mesaji: "Teşekkürler! Pilot başvurunuz bize ulaştı. Ekibimiz en kısa sürede sizinle iletişime geçecek.",
            kvkk_sayfa_slug: "kvkk",
            iletisim_bilgisi_goster: false
        })
    ]
};
/* ------------------------------------------------------------------ */ /* teknoloji                                                           */ /* ------------------------------------------------------------------ */ const teknoloji = {
    slug: "teknoloji",
    baslik: "Teknoloji",
    seo: {
        baslik: "Teknoloji ve Kiosk",
        aciklama: "Samsung 24 inç kiosk, bulut tabanlı yönetim ve çevrimdışı senkronizasyon ile eczane atmosferine uyumlu e-isa deneyimi.",
        og_gorsel: null
    },
    yayin_tarihi: YAYIN,
    revizyon_id: 1,
    bloklar: [
        blok("b_20", "sayfa_basligi", "", {
            rozet: "Teknoloji",
            baslik: "Eczane Atmosferine Uyumlu Modern Kiosk Deneyimi",
            vurgu: "Modern Kiosk Deneyimi",
            alt_metin: "Kompakt donanım, sade arayüz ve merkezi yönetilen yazılım: e-isa, eczanenize teknolojik bir dokunuş katarken operasyonel yük getirmez.",
            butonlar: [
                {
                    etiket: "1 Ay Ücretsiz Pilot",
                    href: "/#pilot",
                    stil: "birincil"
                },
                {
                    etiket: "Nasıl Çalışır?",
                    href: "/#nasil-calisir",
                    stil: "hayalet"
                }
            ]
        }),
        blok("b_21", "gorsel_metin", "", {
            ust_baslik: "Donanım",
            baslik: "Samsung 24\" Kiosk ile Kompakt ve Şık Kurulum",
            metin: "Samsung kiosk'un 24 inçlik kompakt gövdesi, eczane ortamına modern ve teknolojik bir dokunuş katar. Nötr gri-beyaz tonları ve e-isa logosunun kırmızı vurgusu, eczane mimarisiyle uyumlu, güven veren ve yenilikçi bir algı oluşturur.\n\nKurulum için standart bir dergilikten fazla alan gerekmez. Ekran içerikleri ve yazılım güncellemeleri uzaktan, merkezi olarak yönetilir.",
            maddeler: [
                {
                    ikon: "Monitor",
                    metin: "24 inç dokunmatik ekran"
                },
                {
                    ikon: "Storefront",
                    metin: "Dergilik kadar alan kaplar"
                },
                {
                    ikon: "QrCode",
                    metin: "QR / fiş ile dijital sonuç"
                },
                {
                    ikon: "CloudArrowUp",
                    metin: "Uzaktan içerik ve yazılım güncellemesi"
                }
            ],
            gorsel: null,
            gorsel_konumu: "sag",
            butonlar: [],
            arka_plan: "acik"
        }),
        blok("b_22", "ozellik_kartlari", "", {
            ust_baslik: "Öne çıkanlar",
            baslik: "Sade Donanım, Akıllı Yazılım",
            sutun: 4,
            kartlar: [
                {
                    ikon: "Devices",
                    baslik: "Kompakt Yapı",
                    metin: "Eczanenin akışını bozmadan bekleme alanına yerleşir."
                },
                {
                    ikon: "Smiley",
                    baslik: "Modern Deneyim",
                    metin: "Büyük dokunmatik ekranda sade ve anlaşılır bir arayüz."
                },
                {
                    ikon: "QrCode",
                    baslik: "QR / Dijital Sonuç",
                    metin: "Kategori önerisi QR kod veya fiş ile eczacıya aktarılır."
                },
                {
                    ikon: "ArrowsClockwise",
                    baslik: "Bulut + Çevrimdışı Senkron",
                    metin: "Bağlantı kesildiğinde çalışmaya devam eder, bağlantı gelince senkronize olur."
                }
            ],
            arka_plan: "gri"
        }),
        blok("b_23", "sayaclar", "", {
            baslik: "Rakamlarla e-isa",
            ogeler: [
                {
                    deger: 60,
                    sonek: " sn",
                    etiket: "Ortalama etkileşim süresi"
                },
                {
                    deger: 4,
                    onek: "2-",
                    etiket: "Kısa soruyla kategori önerisi"
                },
                {
                    deger: 24,
                    sonek: " inç",
                    etiket: "Dokunmatik kiosk ekranı"
                },
                {
                    deger: 1,
                    sonek: " ay",
                    etiket: "Ücretsiz pilot süreç"
                }
            ],
            arka_plan: "koyu"
        }),
        blok("b_24", "surec_adimlari", "", {
            ust_baslik: "Kurulum",
            baslik: "Dört Adımda Eczanenizde",
            aciklama: "Pilot kararından canlı kullanıma kadar süreci sizin için yönetiyoruz.",
            adimlar: [
                {
                    baslik: "Keşif",
                    metin: "Eczanenizin bekleme alanını ve müşteri akışını birlikte değerlendiririz."
                },
                {
                    baslik: "Kurulum",
                    metin: "Kiosk'u en uygun konuma yerleştirir, bağlantı ve ayarları tamamlarız."
                },
                {
                    baslik: "Eğitim",
                    metin: "Eczane ekibine QR / fiş akışını ve panel kullanımını kısa bir eğitimle anlatırız."
                },
                {
                    baslik: "İzleme",
                    metin: "Pilot süresince etkileşim verilerini birlikte izler, düzenli geri bildirim paylaşırız."
                }
            ],
            arka_plan: "acik"
        }),
        blok("b_25", "cta_banner", "", {
            rozet: "1 ay ücretsiz",
            baslik: "e-isa'yı eczanenizde ücretsiz deneyin",
            metin: "Pilot süreçte veriler konuşsun, kararı siz verin.",
            butonlar: [
                {
                    etiket: "Pilot Başvurusu",
                    href: "/#pilot",
                    stil: "birincil"
                },
                {
                    etiket: "Bize Ulaşın",
                    href: "/iletisim",
                    stil: "ikincil"
                }
            ],
            stil: "koyu"
        })
    ]
};
/* ------------------------------------------------------------------ */ /* sponsorlar                                                          */ /* ------------------------------------------------------------------ */ const sponsorlar = {
    slug: "sponsorlar",
    baslik: "Sponsorlar",
    seo: {
        baslik: "Sponsorluk ve Kurumsal İş Birliği",
        aciklama: "Markanızı, etik iletişim ilkelerine uygun olarak eczane noktasında konumlandırın. e-isa sponsorluk ve kurumsal iş birliği süreci.",
        og_gorsel: null
    },
    yayin_tarihi: YAYIN,
    revizyon_id: 1,
    bloklar: [
        blok("b_30", "sayfa_basligi", "", {
            rozet: "Sponsorluk / Kurumsal İş Birliği",
            baslik: "Geleceğin Eczane Deneyiminde Kurumsal İş Ortağı Olun",
            vurgu: "Kurumsal İş Ortağı",
            alt_metin: "Markanızı, tüketicinin sağlık çözümüne en çok ihtiyaç duyduğu ve güven ortamında bulunduğu eczane noktasında, etik iletişim ilkelerine uygun olarak konumlandırın.",
            butonlar: [
                {
                    etiket: "Sponsorluk Başvurusu",
                    href: "#basvuru",
                    stil: "birincil"
                },
                {
                    etiket: "e-isa Nasıl Çalışır?",
                    href: "/#nasil-calisir",
                    stil: "hayalet"
                }
            ]
        }),
        blok("b_31", "ozellik_kartlari", "", {
            ust_baslik: "Değer önermesi",
            baslik: "Neden e-isa?",
            aciklama: "Eisa Bilişim Teknolojileri A.Ş. olarak geliştirdiğimiz e-isa dijital bilgilendirme ekosistemi, markaların etik iletişim ilkeleriyle doğru noktada konumlanmasını sağlayan yenilikçi bir platformdur.",
            sutun: 3,
            kartlar: [
                {
                    ikon: "Sparkle",
                    baslik: "Görünürlükten Fazlası",
                    metin: "e-isa, markalara yalnızca görünürlük sunmaz; güven ortamında bilgilendirici bir temas noktası oluşturur."
                },
                {
                    ikon: "Storefront",
                    baslik: "Seçkin Eczaneler",
                    metin: "Yüksek hasta potansiyeline sahip, kurumsal hizmet anlayışıyla öne çıkan eczanelerle başlıyoruz."
                },
                {
                    ikon: "Handshake",
                    baslik: "Sınırlı Ortaklık",
                    metin: "Yalnızca sınırlı sayıda stratejik iş ortağı ile ilerliyoruz. İlk paydaşlar arasında yerinizi alın."
                }
            ],
            arka_plan: "gri"
        }),
        blok("b_32", "surec_adimlari", "", {
            ust_baslik: "Süreç",
            baslik: "Sponsorluk Süreci",
            aciklama: "Dört adımda kurumsal iş birliği sürecimizi keşfedin.",
            adimlar: [
                {
                    baslik: "Ön Değerlendirme",
                    metin: "Başvurunuzun ardından ekibimiz, markanıza özel iş birliği çerçevesini paylaşır."
                },
                {
                    baslik: "Kurumsal Sunum",
                    metin: "Markanıza özel konumlandırma yaklaşımını hazırlar ve sunarız."
                },
                {
                    baslik: "Etik Uyum Görüşmesi",
                    metin: "Olası iş birliği fırsatlarını etik iletişim ilkeleriyle birlikte değerlendiririz."
                },
                {
                    baslik: "Ekosisteme Dahil",
                    metin: "Geleceğin eczane deneyiminde doğru temasın değerini birlikte oluştururuz."
                }
            ],
            arka_plan: "acik"
        }),
        blok("b_33", "logo_bandi", "", {
            baslik: "İş Ortaklarımız",
            logolar: [],
            bos_mesaj: "İlk iş ortaklarımızla görüşmelerimiz sürüyor. Bu alanda yerinizi almak için başvurun."
        }),
        blok("b_34", "basvuru_formu", "basvuru", {
            ust_baslik: "İlk paydaşlar arasında olun",
            baslik: "Sponsorluk Başvurusu",
            aciklama: "Başvurunuzun ardından ekibimiz, markanıza özel hazırlanan iş birliği modelini paylaşır ve süreci başlatır.",
            form_tipi: "sponsor",
            maddeler: [],
            basari_mesaji: "Teşekkürler! Sponsorluk başvurunuz bize ulaştı. Ekibimiz en kısa sürede sizinle iletişime geçecek.",
            kvkk_sayfa_slug: "kvkk",
            iletisim_bilgisi_goster: false
        })
    ]
};
/* ------------------------------------------------------------------ */ /* hakkimizda                                                          */ /* ------------------------------------------------------------------ */ const hakkimizda = {
    slug: "hakkimizda",
    baslik: "Hakkımızda",
    seo: {
        baslik: "Hakkımızda",
        aciklama: "Eisa Bilişim Teknolojileri A.Ş., eczacıyı merkeze alan dijital sağlık okuryazarlığı çözümü e-isa'yı geliştirir.",
        og_gorsel: null
    },
    yayin_tarihi: YAYIN,
    revizyon_id: 1,
    bloklar: [
        blok("b_40", "sayfa_basligi", "", {
            rozet: "Hakkımızda",
            baslik: "Eczacıyı Merkeze Alan Dijital Sağlık Okuryazarlığı",
            vurgu: "Dijital Sağlık Okuryazarlığı",
            alt_metin: "Eisa Bilişim Teknolojileri A.Ş. olarak eczane içindeki kısa bekleme anlarını, eczacının uzmanlığını destekleyen anlamlı bir hazırlığa dönüştürüyoruz.",
            butonlar: []
        }),
        blok("b_41", "gorsel_metin", "", {
            ust_baslik: "Hikâyemiz",
            baslik: "Bekleme Süresini Anlamlı Bir Ana Dönüştürme Fikri",
            metin: "Eczaneye gelen pek çok kişi, reçetesi hazırlanırken birkaç dakika bekler. Bu süre çoğu zaman sessizce geçer; oysa kişinin kendi ihtiyaçlarını düşünmesi ve eczacısıyla daha odaklı bir görüşme yapması için değerli bir fırsattır.\n\ne-isa bu fikirden doğdu: kişiyi karmaşık terimlerle yormadan, birkaç kısa soruyla ihtiyacını fark etmesine yardımcı olan ve sonucu eczacının değerlendirmesine sunan sade bir dijital deneyim. Teşhis koymayan, marka önermeyen ve kararı her zaman eczacıya bırakan bir yaklaşım.",
            maddeler: [
                {
                    ikon: "Target",
                    metin: "Eczacının danışmanlık rolünü güçlendirmek"
                },
                {
                    ikon: "Heart",
                    metin: "Kişinin sağlık okuryazarlığını desteklemek"
                },
                {
                    ikon: "Lightbulb",
                    metin: "Teknolojiyi sade ve anlaşılır tutmak"
                }
            ],
            gorsel: null,
            gorsel_konumu: "sol",
            butonlar: [],
            arka_plan: "acik"
        }),
        blok("b_42", "ozellik_kartlari", "", {
            ust_baslik: "Değerlerimiz",
            baslik: "Bizi Yönlendiren İlkeler",
            sutun: 4,
            kartlar: [
                {
                    ikon: "UserCircle",
                    baslik: "Eczacı Merkezli",
                    metin: "Her kararın sahibi eczacıdır; e-isa yalnızca ön hazırlık yapar."
                },
                {
                    ikon: "ShieldCheck",
                    baslik: "Etik",
                    metin: "Teşhis, tedavi veya marka yönlendirmesi yapmayız; içerikleri denetleriz."
                },
                {
                    ikon: "ChartLineUp",
                    baslik: "Veri Odaklı",
                    metin: "Varsayımlar yerine pilot verileriyle birlikte değerlendiririz."
                },
                {
                    ikon: "Lightbulb",
                    baslik: "Sade Teknoloji",
                    metin: "Karmaşık olanı arka planda çözer, ekranda yalın bir deneyim sunarız."
                }
            ],
            arka_plan: "gri"
        }),
        blok("b_43", "ekip", "", {
            ust_baslik: "Ekip",
            baslik: "e-isa'nın Arkasındakiler",
            aciklama: "Sağlık, yazılım ve saha deneyimini bir araya getiren küçük ve odaklı bir ekibiz.",
            kisiler: [
                {
                    ad_soyad: "Yasin ÖZGÜL",
                    unvan: "Yazılım Mimarı",
                    biyografi: "e-isa platformunun yazılım mimarisini, kiosk ve bulut altyapısını tasarlar. Güvenilir, sade ve ölçeklenebilir sistemler kurmaya odaklanır.",
                    foto: null,
                    linkedin: ""
                }
            ]
        }),
        blok("b_44", "cta_banner", "", {
            baslik: "Birlikte daha bilinçli bir eczane deneyimi kuralım",
            metin: "Pilot süreç, iş birliği veya sorularınız için bize ulaşın.",
            butonlar: [
                {
                    etiket: "İletişime Geçin",
                    href: "/iletisim",
                    stil: "birincil"
                },
                {
                    etiket: "Pilot Süreci İncele",
                    href: "/#pilot",
                    stil: "hayalet"
                }
            ],
            stil: "kirmizi"
        })
    ]
};
/* ------------------------------------------------------------------ */ /* iletisim                                                            */ /* ------------------------------------------------------------------ */ const iletisim = {
    slug: "iletisim",
    baslik: "İletişim",
    seo: {
        baslik: "İletişim",
        aciklama: "e-isa hakkında bilgi almak, pilot süreç başvurusu yapmak veya sorularınızı iletmek için bize ulaşın.",
        og_gorsel: null
    },
    yayin_tarihi: YAYIN,
    revizyon_id: 1,
    bloklar: [
        blok("b_50", "sayfa_basligi", "", {
            rozet: "İletişim",
            baslik: "Bizimle İletişime Geçin",
            vurgu: "İletişime Geçin",
            alt_metin: "e-isa hakkında daha fazla bilgi almak, pilot süreç başvurusu yapmak veya sorularınızı iletmek için bize yazabilirsiniz.",
            butonlar: []
        }),
        blok("b_51", "basvuru_formu", "", {
            ust_baslik: "İletişim formu",
            baslik: "Mesajınızı Bırakın",
            aciklama: "Formu doldurun, ekibimiz en kısa sürede size dönüş yapsın.",
            form_tipi: "genel",
            maddeler: [],
            basari_mesaji: "Teşekkürler! Mesajınız bize ulaştı. En kısa sürede size dönüş yapacağız.",
            kvkk_sayfa_slug: "kvkk",
            iletisim_bilgisi_goster: true
        })
    ]
};
/* ------------------------------------------------------------------ */ /* kvkk                                                                */ /* ------------------------------------------------------------------ */ const KVKK_HTML = `
<p>Eisa Bilişim Teknolojileri A.Ş. (“Şirket”) olarak kişisel verilerinizin güvenliğine önem veriyoruz. Bu aydınlatma metni, 6698 sayılı Kişisel Verilerin Korunması Kanunu (“KVKK”) m.10 uyarınca, eisa.com.tr internet sitesi üzerinden işlenen kişisel verileriniz hakkında sizi bilgilendirmek amacıyla hazırlanmıştır.</p>
<h2>1. Veri Sorumlusu</h2>
<p>KVKK kapsamında veri sorumlusu Eisa Bilişim Teknolojileri A.Ş.'dir. Bize <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresinden ulaşabilirsiniz.</p>
<h2>2. İşlenen Kişisel Veriler</h2>
<p>İnternet sitemizdeki pilot başvurusu, sponsorluk başvurusu ve iletişim formları aracılığıyla aşağıdaki veriler işlenebilir:</p>
<ul>
<li><strong>Kimlik bilgileri:</strong> ad, soyad</li>
<li><strong>İletişim bilgileri:</strong> e-posta adresi, telefon numarası, il</li>
<li><strong>Mesleki bilgiler:</strong> kurum / eczane adı</li>
<li><strong>Talep bilgileri:</strong> form aracılığıyla ilettiğiniz mesaj içeriği</li>
<li><strong>İşlem güvenliği bilgileri:</strong> kötüye kullanımı önlemek amacıyla IP adresinden türetilen ve geri döndürülemez biçimde saklanan özet (hash) değeri</li>
</ul>
<p>Formlarımız sağlık verisi toplamak amacıyla tasarlanmamıştır; lütfen mesaj alanına sağlık durumunuza ilişkin bilgi yazmayınız.</p>
<h2>3. İşleme Amaçları</h2>
<ul>
<li>Başvuru ve taleplerinizin alınması, değerlendirilmesi ve size dönüş yapılması,</li>
<li>Pilot süreç ve iş birliği görüşmelerinin yürütülmesi,</li>
<li>İnternet sitesinin güvenliğinin sağlanması ve kötüye kullanımın önlenmesi,</li>
<li>Hukuki yükümlülüklerin yerine getirilmesi.</li>
</ul>
<h2>4. Hukuki Sebepler</h2>
<p>Kişisel verileriniz KVKK m.5/2 uyarınca; bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması (c), veri sorumlusunun hukuki yükümlülüğünü yerine getirebilmesi (ç) ve ilgili kişinin temel hak ve özgürlüklerine zarar vermemek kaydıyla veri sorumlusunun meşru menfaati (f) hukuki sebeplerine dayanılarak işlenir.</p>
<h2>5. Aktarım</h2>
<p>Kişisel verileriniz yurt içinde barındırılan sunucularda saklanır. Hukuken yetkili kamu kurum ve kuruluşlarının talepleri dışında üçüncü kişilerle paylaşılmaz.</p>
<h2>6. Toplama Yöntemi</h2>
<p>Kişisel verileriniz, internet sitemizdeki formları doldurmanız yoluyla elektronik ortamda toplanır.</p>
<h2>7. Saklama Süresi</h2>
<p>Başvuru verileri, talebin sonuçlandırılmasından itibaren ilgili mevzuatta öngörülen veya işleme amacının gerektirdiği süre boyunca saklanır; sürenin sonunda silinir, yok edilir veya anonim hale getirilir.</p>
<h2>8. İlgili Kişinin Hakları</h2>
<p>KVKK m.11 uyarınca; kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse buna ilişkin bilgi talep etme, işleme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme, aktarıldığı üçüncü kişileri bilme, eksik veya yanlış işlenmişse düzeltilmesini, KVKK m.7 çerçevesinde silinmesini veya yok edilmesini isteme, bu işlemlerin aktarıldığı üçüncü kişilere bildirilmesini isteme, münhasıran otomatik sistemlerle analiz edilmesi sonucu aleyhinize bir sonucun ortaya çıkmasına itiraz etme ve kanuna aykırı işleme sebebiyle zarara uğramanız hâlinde zararın giderilmesini talep etme haklarına sahipsiniz.</p>
<h2>9. Başvuru</h2>
<p>Haklarınıza ilişkin taleplerinizi <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresine iletebilirsiniz. Başvurular en geç otuz gün içinde ücretsiz olarak sonuçlandırılır.</p>
`.trim();
const kvkk = {
    slug: "kvkk",
    baslik: "KVKK Aydınlatma Metni",
    seo: {
        baslik: "KVKK Aydınlatma Metni",
        aciklama: "6698 sayılı KVKK kapsamında eisa.com.tr üzerinden işlenen kişisel veriler hakkında aydınlatma metni.",
        og_gorsel: null
    },
    yayin_tarihi: YAYIN,
    revizyon_id: 1,
    bloklar: [
        blok("b_60", "sayfa_basligi", "", {
            rozet: "Yasal",
            baslik: "KVKK Aydınlatma Metni",
            alt_metin: "6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında bilgilendirme.",
            butonlar: []
        }),
        blok("b_61", "zengin_metin", "", {
            icerik_html: KVKK_HTML,
            genislik: "dar",
            son_guncelleme: "7 Kasım 2026"
        })
    ]
};
/* ------------------------------------------------------------------ */ /* cerez-politikasi                                                    */ /* ------------------------------------------------------------------ */ const CEREZ_HTML = `
<p>Bu Çerez Politikası, Eisa Bilişim Teknolojileri A.Ş. tarafından işletilen eisa.com.tr internet sitesinde kullanılan çerezler hakkında sizi bilgilendirmek amacıyla hazırlanmıştır.</p>
<h2>Çerez Nedir?</h2>
<p>Çerezler, bir internet sitesini ziyaret ettiğinizde tarayıcınız aracılığıyla cihazınıza kaydedilen küçük metin dosyalarıdır. Sitenin düzgün çalışmasını, tercihlerinizin hatırlanmasını ve güvenliğin sağlanmasını mümkün kılar.</p>
<h2>Kullandığımız Çerezler</h2>
<h3>Zorunlu çerezler</h3>
<p>Sitenin temel işlevleri için gereklidir ve kapatılamaz. Örneğin çerez bilgilendirme tercihinizin hatırlanması ve form güvenliği bu kapsamdadır. Bu çerezler kişisel tercih veya pazarlama amacıyla kullanılmaz.</p>
<table>
<thead><tr><th>Ad</th><th>Amaç</th><th>Süre</th></tr></thead>
<tbody>
<tr><td>eisa_cerez_bilgi</td><td>Çerez bilgilendirmesini gördüğünüzü hatırlar (tarayıcı yerel depolaması)</td><td>Kalıcı</td></tr>
<tr><td>__prerender_bypass, eisa_preview</td><td>Yalnızca içerik editörlerinin önizleme oturumu</td><td>Oturum</td></tr>
</tbody>
</table>
<h3>Analitik çerezler</h3>
<p>Şu anda sitemizde analitik veya pazarlama çerezi kullanılmamaktadır. İleride ziyaret istatistiklerini anlamak amacıyla analitik çerezler kullanılmaya başlanırsa, bu çerezler yalnızca açık onayınızla etkinleştirilecek ve bu politika güncellenecektir.</p>
<h2>Çerezleri Nasıl Yönetebilirsiniz?</h2>
<p>Tarayıcınızın ayarlarından çerezleri silebilir veya engelleyebilirsiniz. Zorunlu çerezlerin engellenmesi durumunda sitenin bazı bölümleri beklendiği gibi çalışmayabilir.</p>
<h2>İletişim</h2>
<p>Çerezler ve kişisel verileriniz hakkındaki sorularınız için <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresine yazabilirsiniz. Ayrıntılı bilgi için <a href="/kvkk">KVKK Aydınlatma Metni</a>'ni inceleyebilirsiniz.</p>
`.trim();
const cerezPolitikasi = {
    slug: "cerez-politikasi",
    baslik: "Çerez Politikası",
    seo: {
        baslik: "Çerez Politikası",
        aciklama: "eisa.com.tr internet sitesinde kullanılan zorunlu ve analitik çerezler ve çerez yönetimi hakkında bilgi.",
        og_gorsel: null
    },
    yayin_tarihi: YAYIN,
    revizyon_id: 1,
    bloklar: [
        blok("b_70", "sayfa_basligi", "", {
            rozet: "Yasal",
            baslik: "Çerez Politikası",
            alt_metin: "Sitemizde hangi çerezlerin neden kullanıldığını ve nasıl yönetebileceğinizi açıklıyoruz.",
            butonlar: []
        }),
        blok("b_71", "zengin_metin", "", {
            icerik_html: CEREZ_HTML,
            genislik: "dar",
            son_guncelleme: "7 Kasım 2026"
        })
    ]
};
const mockSayfalar = {
    anasayfa,
    teknoloji,
    sponsorlar,
    hakkimizda,
    iletisim,
    kvkk,
    "cerez-politikasi": cerezPolitikasi
};
}),
"[project]/src/lib/mock/site.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/**
 * MOCK: `GET /api/website/public/site/` — CONTRACT §9 seed ayarları ve menüleri.
 * Backend kapalıyken `getSite()` için yedek (fallback) olarak da kullanılır.
 */ __turbopack_context__.s([
    "mockSite",
    ()=>mockSite
]);
const mockSite = {
    ayarlar: {
        site_adi: "e-isa",
        seo_baslik_sablonu: "%s | e-isa",
        seo_aciklama: "e-isa, eczanelerde reçete bekleme süresini yapay zeka destekli sağlık okuryazarlığı ve eczacı kontrollü danışmanlık deneyimine dönüştüren modern kiosk ekosistemidir.",
        og_gorsel: null,
        eposta: "iletisim@eisa.com.tr",
        telefon: "",
        whatsapp: "",
        adres: "",
        firma_unvani: "Eisa Bilişim Teknolojileri A.Ş.",
        footer_aciklama: "e-isa; eczanedeki bekleme süresini kategori bazlı sağlık okuryazarlığına dönüştüren, eczacının kontrolünü merkeze alan dijital ön hazırlık asistanıdır. Tıbbi teşhis veya tedavi sistemi değildir; son değerlendirme her zaman eczacıdadır.",
        sosyal_linkler: [
            {
                platform: "linkedin",
                url: "https://www.linkedin.com/company/e-isa"
            },
            {
                platform: "instagram",
                url: "https://www.instagram.com/eisa.tr/"
            }
        ]
    },
    menuler: {
        header: [
            {
                id: 1,
                etiket: "Çözüm",
                href: "/#nasil-calisir",
                yeni_sekme: false,
                cta: false,
                cocuklar: [
                    {
                        id: 2,
                        etiket: "Nasıl Çalışır?",
                        href: "/#nasil-calisir",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 3,
                        etiket: "Eczacı Kontrolü",
                        href: "/#eczaci-kontrolu",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 4,
                        etiket: "Müşteri Yolculuğu",
                        href: "/#yolculuk",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 5,
                        etiket: "Kazanç Modeli",
                        href: "/#kazanc",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 6,
                        etiket: "SSS",
                        href: "/#sss",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    }
                ]
            },
            {
                id: 7,
                etiket: "Teknoloji",
                href: "/teknoloji",
                yeni_sekme: false,
                cta: false,
                cocuklar: []
            },
            {
                id: 8,
                etiket: "Sponsorlar",
                href: "/sponsorlar",
                yeni_sekme: false,
                cta: false,
                cocuklar: []
            },
            {
                id: 9,
                etiket: "Blog",
                href: "/blog",
                yeni_sekme: false,
                cta: false,
                cocuklar: []
            },
            {
                id: 10,
                etiket: "Kurumsal",
                href: "/hakkimizda",
                yeni_sekme: false,
                cta: false,
                cocuklar: [
                    {
                        id: 11,
                        etiket: "Hakkımızda",
                        href: "/hakkimizda",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 12,
                        etiket: "İletişim",
                        href: "/iletisim",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    }
                ]
            },
            {
                id: 13,
                etiket: "1 Ay Ücretsiz Pilot",
                href: "/#pilot",
                yeni_sekme: false,
                cta: true,
                cocuklar: []
            }
        ],
        footer: [
            {
                id: 20,
                etiket: "Ürün",
                href: "/",
                yeni_sekme: false,
                cta: false,
                cocuklar: [
                    {
                        id: 21,
                        etiket: "Nasıl Çalışır?",
                        href: "/#nasil-calisir",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 22,
                        etiket: "Teknoloji",
                        href: "/teknoloji",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 23,
                        etiket: "Kazanç Modeli",
                        href: "/#kazanc",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 24,
                        etiket: "SSS",
                        href: "/#sss",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    }
                ]
            },
            {
                id: 25,
                etiket: "Kurumsal",
                href: "/hakkimizda",
                yeni_sekme: false,
                cta: false,
                cocuklar: [
                    {
                        id: 26,
                        etiket: "Hakkımızda",
                        href: "/hakkimizda",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 27,
                        etiket: "Sponsorlar",
                        href: "/sponsorlar",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 28,
                        etiket: "Blog",
                        href: "/blog",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    },
                    {
                        id: 29,
                        etiket: "İletişim",
                        href: "/iletisim",
                        yeni_sekme: false,
                        cta: false,
                        cocuklar: []
                    }
                ]
            }
        ],
        footer_alt: [
            {
                id: 30,
                etiket: "KVKK Aydınlatma Metni",
                href: "/kvkk",
                yeni_sekme: false,
                cta: false,
                cocuklar: []
            },
            {
                id: 31,
                etiket: "Çerez Politikası",
                href: "/cerez-politikasi",
                yeni_sekme: false,
                cta: false,
                cocuklar: []
            }
        ]
    }
};
}),
"[project]/src/lib/utils.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "anchorIceriyor",
    ()=>anchorIceriyor,
    "cn",
    ()=>cn,
    "disLinkMi",
    ()=>disLinkMi,
    "hrefAyir",
    ()=>hrefAyir,
    "icLinkMi",
    ()=>icLinkMi,
    "paraFormatla",
    ()=>paraFormatla,
    "paragraflaraBol",
    ()=>paragraflaraBol,
    "sayiFormatla",
    ()=>sayiFormatla,
    "semaLinkiMi",
    ()=>semaLinkiMi,
    "slugYolu",
    ()=>slugYolu,
    "tarihFormatla",
    ()=>tarihFormatla,
    "vurguParcala",
    ()=>vurguParcala,
    "yolNormalize",
    ()=>yolNormalize
]);
/**
 * Genel yardımcılar — sunucu ve istemci tarafında kullanılabilir.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$clsx$2f$dist$2f$clsx$2e$mjs__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/clsx/dist/clsx.mjs [app-route] (ecmascript)");
;
function cn(...girdiler) {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$clsx$2f$dist$2f$clsx$2e$mjs__$5b$app$2d$route$5d$__$28$ecmascript$29$__["clsx"])(girdiler);
}
function paragraflaraBol(metin) {
    if (!metin) return [];
    return metin.replace(/\r\n/g, "\n").split(/\n\s*\n/).map((p)=>p.trim()).filter(Boolean);
}
function vurguParcala(baslik, vurgu) {
    if (!vurgu || !baslik.includes(vurgu)) return [
        {
            metin: baslik,
            vurgu: false
        }
    ];
    const i = baslik.indexOf(vurgu);
    return [
        {
            metin: baslik.slice(0, i),
            vurgu: false
        },
        {
            metin: vurgu,
            vurgu: true
        },
        {
            metin: baslik.slice(i + vurgu.length),
            vurgu: false
        }
    ].filter((p)=>p.metin.length > 0);
}
const sayiBicimi = new Intl.NumberFormat("tr-TR");
function sayiFormatla(deger, secenekler) {
    return secenekler ? new Intl.NumberFormat("tr-TR", secenekler).format(deger) : sayiBicimi.format(deger);
}
function paraFormatla(deger, paraBirimi = "TL") {
    return `${sayiBicimi.format(deger)} ${paraBirimi}`.trim();
}
function tarihFormatla(iso) {
    if (!iso) return "";
    const t = new Date(iso);
    if (Number.isNaN(t.getTime())) return "";
    return new Intl.DateTimeFormat("tr-TR", {
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone: "Europe/Istanbul"
    }).format(t);
}
function anchorIceriyor(href) {
    return href.startsWith("#") || href.startsWith("/") && href.includes("#");
}
function icLinkMi(href) {
    return href.startsWith("/") && !href.startsWith("//");
}
function disLinkMi(href) {
    return /^https?:\/\//i.test(href) || href.startsWith("//");
}
function semaLinkiMi(href) {
    return /^(mailto|tel|sms):/i.test(href);
}
function hrefAyir(href) {
    const i = href.indexOf("#");
    if (i === -1) return {
        yol: href || null,
        hash: null
    };
    const yol = href.slice(0, i) || null;
    const hash = decodeURIComponent(href.slice(i + 1)) || null;
    return {
        yol,
        hash
    };
}
function yolNormalize(yol) {
    if (!yol) return "/";
    const temiz = yol.split("?")[0].replace(/\/+$/, "");
    return temiz === "" ? "/" : temiz;
}
function slugYolu(slug) {
    return slug === "anasayfa" ? "/" : `/${slug}`;
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__0g41h98pb9m-z._.js.map