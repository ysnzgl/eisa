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
"[externals]/node:crypto [external] (node:crypto, cjs)", ((__turbopack_context__, module, exports) => {

var mod = __turbopack_context__.x("node:crypto", () => require("node:crypto"));

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
"[project]/src/app/api/revalidate/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>POST
]);
/**
 * On-demand revalidation webhook'u (CONTRACT §6).
 *
 *   POST /api/revalidate
 *   Header: X-Revalidate-Secret: <REVALIDATE_SECRET>
 *   Gövde:  { "tags": ["sayfa:anasayfa", "sayfalar", "site"] }
 *   Yanıt:  200 { "revalidated": [...] } | 401 (yanlış secret) | 400 (geçersiz gövde)
 *
 * Backend publish sonrası her pod'a ayrı ayrı çağırır (headless service fan-out).
 * `revalidateTag(tag, { expire: 0 })`: dış webhook için önerilen biçim — sonraki istek taze veriyle üretilir.
 */ var __TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$crypto__$5b$external$5d$__$28$node$3a$crypto$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/node:crypto [external] (node:crypto, cjs)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$cache$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/cache.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/env.ts [app-route] (ecmascript)");
;
;
;
/** İzinli tag biçimleri: site, sayfalar, blog, sayfa:<slug>, blog:<slug> */ const TAG_DESENI = /^(site|sayfalar|blog|sayfa:[a-z0-9-]+|blog:[a-z0-9-]+)$/;
function sirEsitMi(gelen, beklenen) {
    const a = Buffer.from(gelen);
    const b = Buffer.from(beklenen);
    if (a.length !== b.length) {
        // Uzunluk sızdırmamak için yine de sabit süreli karşılaştırma yap.
        (0, __TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$crypto__$5b$external$5d$__$28$node$3a$crypto$2c$__cjs$29$__["timingSafeEqual"])(b, b);
        return false;
    }
    return (0, __TURBOPACK__imported__module__$5b$externals$5d2f$node$3a$crypto__$5b$external$5d$__$28$node$3a$crypto$2c$__cjs$29$__["timingSafeEqual"])(a, b);
}
async function POST(istek) {
    const sir = istek.headers.get("x-revalidate-secret") ?? "";
    if (!sir || !sirEsitMi(sir, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["env"].revalidateSecret)) {
        return Response.json({
            hata: "Yetkisiz."
        }, {
            status: 401
        });
    }
    let govde;
    try {
        govde = await istek.json();
    } catch  {
        return Response.json({
            hata: "Geçersiz JSON gövdesi."
        }, {
            status: 400
        });
    }
    const tags = govde?.tags;
    if (!Array.isArray(tags)) {
        return Response.json({
            hata: "`tags` dizisi zorunludur."
        }, {
            status: 400
        });
    }
    const revalidated = [];
    const atlanan = [];
    for (const t of tags){
        if (typeof t === "string" && t.length <= 256 && TAG_DESENI.test(t)) {
            (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$cache$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["revalidateTag"])(t, {
                expire: 0
            });
            revalidated.push(t);
        } else {
            atlanan.push(String(t).slice(0, 100));
        }
    }
    if (atlanan.length) console.warn(`[e-isa revalidate] tanınmayan tag'ler atlandı: ${atlanan.join(", ")}`);
    console.info(`[e-isa revalidate] ${revalidated.join(", ") || "(yok)"}`);
    return Response.json({
        revalidated,
        ...atlanan.length ? {
            atlanan
        } : {}
    });
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
];

//# sourceMappingURL=%5Broot-of-the-server%5D__1_hcbimpigla8._.js.map