module.exports = [
"[project]/src/components/ui/MediaImage.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "MediaImage",
    ()=>MediaImage
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
/**
 * CMS medyası için next/image sarmalayıcısı. `MEDIA_BASE_URL + yol` otomatik eklenir.
 *
 *   <MediaImage medya={veri.gorsel} sizes="(min-width: 1024px) 50vw, 100vw" className="rounded-kart" />
 *   <MediaImage medya={kisi.foto} fill sizes="200px"><VarsayilanAvatar /></MediaImage>  // null → children
 *
 * - `fill` verilmezse ve medyada genişlik/yükseklik varsa intrinsic boyutla render eder;
 *   boyut bilinmiyorsa otomatik `fill` moduna geçer (ebeveyn `relative` + boyutlu olmalı).
 * - `alt` medyadaki `alt` alanından gelir; `alt` prop'u ile ezilebilir (dekoratifse alt="").
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$image$2d$component$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__Image__as__default$3e$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/image-component.js [app-ssr] (ecmascript) <export Image as default>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$SiteProvider$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/components/SiteProvider.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$media$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/media.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
;
function MediaImage({ medya, children, alt, fill, sizes, priority, className, quality }) {
    const url = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$SiteProvider$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useMediaUrl"])();
    if (!(0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$media$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["medyaVarMi"])(medya)) return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Fragment"], {
        children: children ?? null
    }, void 0, false, {
        fileName: "[project]/src/components/ui/MediaImage.tsx",
        lineNumber: 35,
        columnNumber: 34
    }, this);
    const src = url(medya.yol);
    if (!src) return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Fragment"], {
        children: children ?? null
    }, void 0, false, {
        fileName: "[project]/src/components/ui/MediaImage.tsx",
        lineNumber: 37,
        columnNumber: 20
    }, this);
    const altMetin = alt ?? medya.alt ?? "";
    const boyutVar = Boolean(medya.genislik && medya.yukseklik);
    if (fill || !boyutVar) {
        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$image$2d$component$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__Image__as__default$3e$__["default"], {
            src: src,
            alt: altMetin,
            fill: true,
            sizes: sizes ?? "100vw",
            priority: priority,
            quality: quality,
            className: className ?? "object-cover"
        }, void 0, false, {
            fileName: "[project]/src/components/ui/MediaImage.tsx",
            lineNumber: 44,
            columnNumber: 7
        }, this);
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$image$2d$component$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__Image__as__default$3e$__["default"], {
        src: src,
        alt: altMetin,
        width: medya.genislik ?? undefined,
        height: medya.yukseklik ?? undefined,
        sizes: sizes,
        priority: priority,
        quality: quality,
        className: className
    }, void 0, false, {
        fileName: "[project]/src/components/ui/MediaImage.tsx",
        lineNumber: 57,
        columnNumber: 5
    }, this);
}
}),
"[project]/src/components/ui/Reveal.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "Reveal",
    ()=>Reveal,
    "Stagger",
    ()=>Stagger,
    "StaggerItem",
    ()=>StaggerItem
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
/**
 * Scroll reveal animasyonları (motion `whileInView`, bir kez).
 *
 *   <Reveal>...</Reveal>                         // aşağıdan yukarı belirme
 *   <Reveal yon="sol" gecikme={0.1}>...</Reveal>
 *   <Stagger className="grid ..."><StaggerItem>…</StaggerItem>…</Stagger>
 *
 * prefers-reduced-motion açıksa içerik animasyonsuz, anında görünür hale gelir.
 * (Hidrasyon uyumu için element tipi değişmez; yalnızca hedef değerlere süre 0 ile geçilir.)
 * Server component içinde kullanılabilir (children sunucuda render edilir).
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/motion/dist/es/react.mjs [app-ssr] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$hareket$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/hareket.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$hooks$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/hooks.ts [app-ssr] (ecmascript)");
"use client";
;
;
;
;
const HEDEF = {
    opacity: 1,
    x: 0,
    y: 0
};
function baslangic(yon, mesafe) {
    switch(yon){
        case "yukari":
            return {
                opacity: 0,
                y: mesafe
            };
        case "asagi":
            return {
                opacity: 0,
                y: -mesafe
            };
        case "sol":
            return {
                opacity: 0,
                x: mesafe
            };
        case "sag":
            return {
                opacity: 0,
                x: -mesafe
            };
        default:
            return {
                opacity: 0
            };
    }
}
/** Modül seviyesinde sabit harita: render sırasında bileşen üretilmez. */ const MOTION = {
    div: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].div,
    section: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].section,
    article: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].article,
    li: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].li,
    ul: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].ul,
    ol: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].ol,
    dl: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].dl,
    span: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].span,
    p: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].p,
    header: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].header,
    figure: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$motion$2f$dist$2f$es$2f$react$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["motion"].figure
};
function Reveal({ children, as = "div", className, yon = "yukari", mesafe = 24, gecikme = 0, sure = 0.7, esik = 0.2, id }) {
    const azHareket = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$hooks$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useAzHareket"])();
    const M = MOTION[as];
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(M, {
        id: id,
        className: className,
        initial: baslangic(yon, mesafe),
        whileInView: HEDEF,
        animate: azHareket ? HEDEF : undefined,
        viewport: {
            once: true,
            amount: esik
        },
        transition: azHareket ? {
            duration: 0
        } : {
            duration: sure,
            delay: gecikme,
            ease: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$hareket$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["EASE_EISA"]
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/src/components/ui/Reveal.tsx",
        lineNumber: 86,
        columnNumber: 5
    }, this);
}
function Stagger({ children, as = "div", className, aralik = 0.08, gecikme = 0, esik = 0.15 }) {
    const azHareket = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$hooks$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useAzHareket"])();
    const M = MOTION[as];
    const varyant = {
        gizli: {},
        gorunur: {
            transition: azHareket ? {
                staggerChildren: 0
            } : {
                staggerChildren: aralik,
                delayChildren: gecikme
            }
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(M, {
        className: className,
        variants: varyant,
        initial: "gizli",
        whileInView: "gorunur",
        animate: azHareket ? "gorunur" : undefined,
        viewport: {
            once: true,
            amount: esik
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/src/components/ui/Reveal.tsx",
        lineNumber: 123,
        columnNumber: 5
    }, this);
}
function StaggerItem({ children, as = "div", className, yon = "yukari", mesafe = 24, sure = 0.6 }) {
    const azHareket = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$hooks$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useAzHareket"])();
    const M = MOTION[as];
    const varyant = {
        gizli: baslangic(yon, mesafe),
        gorunur: {
            ...HEDEF,
            transition: azHareket ? {
                duration: 0
            } : {
                duration: sure,
                ease: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$hareket$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["EASE_EISA"]
            }
        }
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(M, {
        className: className,
        variants: varyant,
        children: children
    }, void 0, false, {
        fileName: "[project]/src/components/ui/Reveal.tsx",
        lineNumber: 153,
        columnNumber: 5
    }, this);
}
}),
];

//# sourceMappingURL=src_components_ui_0g7l1n8ybmu9v._.js.map