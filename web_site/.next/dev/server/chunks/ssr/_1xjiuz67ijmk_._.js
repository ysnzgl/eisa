module.exports = [
"[project]/.next-internal/server/app/[[...slug]]/page/actions.js { ACTIONS_MODULE0 => \"[project]/src/app/actions/basvuru.ts [app-rsc] (ecmascript)\" } [app-rsc] (server actions loader, ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "60d94374f20878874fb67ce4e3ee2857f4d28230ac",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$app$2f$actions$2f$basvuru$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["basvuruGonder"]
]);
var __TURBOPACK__imported__module__$5b$project$5d2f2e$next$2d$internal$2f$server$2f$app$2f5b5b2e2e2e$slug$5d5d2f$page$2f$actions$2e$js__$7b$__ACTIONS_MODULE0__$3d3e$__$225b$project$5d2f$src$2f$app$2f$actions$2f$basvuru$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$2922$__$7d$__$5b$app$2d$rsc$5d$__$28$server__actions__loader$2c$__ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i('[project]/.next-internal/server/app/[[...slug]]/page/actions.js { ACTIONS_MODULE0 => "[project]/src/app/actions/basvuru.ts [app-rsc] (ecmascript)" } [app-rsc] (server actions loader, ecmascript) <locals>');
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$app$2f$actions$2f$basvuru$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/app/actions/basvuru.ts [app-rsc] (ecmascript)");
}),
"[project]/.next-internal/server/app/[[...slug]]/page/actions.js { ACTIONS_MODULE0 => \"[project]/src/app/actions/basvuru.ts [app-rsc] (ecmascript)\" } [app-rsc] (server actions loader, ecmascript) <locals>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([]);
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$app$2f$actions$2f$basvuru$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/app/actions/basvuru.ts [app-rsc] (ecmascript)");
;
}),
"[project]/node_modules/next/dist/build/webpack/loaders/next-flight-loader/action-validate.js [app-rsc] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

// This function ensures that all the exported values are valid server actions,
// during the runtime. By definition all actions are required to be async
// functions, but here we can only check that they are functions.
Object.defineProperty(exports, "__esModule", {
    value: true
});
Object.defineProperty(exports, "ensureServerEntryExports", {
    enumerable: true,
    get: function() {
        return ensureServerEntryExports;
    }
});
function ensureServerEntryExports(actions) {
    for(let i = 0; i < actions.length; i++){
        const action = actions[i];
        if (typeof action !== 'function') {
            throw new Error(`A "use server" file can only export async functions, found ${typeof action}.\nRead more: https://nextjs.org/docs/messages/invalid-use-server-value`);
        }
    }
}
}),
"[project]/node_modules/next/dist/build/webpack/loaders/next-flight-loader/server-reference.js [app-rsc] (ecmascript)", ((__turbopack_context__, module, exports) => {
"use strict";

/* eslint-disable import/no-extraneous-dependencies */ Object.defineProperty(exports, "__esModule", {
    value: true
});
Object.defineProperty(exports, "registerServerReference", {
    enumerable: true,
    get: function() {
        return _server.registerServerReference;
    }
});
const _server = __turbopack_context__.r("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/rsc/react-server-dom-turbopack-server.js [app-rsc] (ecmascript)");
}),
"[project]/src/app/actions/basvuru.ts [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/* __next_internal_action_entry_do_not_use__ [{"60d94374f20878874fb67ce4e3ee2857f4d28230ac":{"name":"basvuruGonder"}},"src/app/actions/basvuru.ts",""] */ __turbopack_context__.s([
    "basvuruGonder",
    ()=>basvuruGonder
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$webpack$2f$loaders$2f$next$2d$flight$2d$loader$2f$server$2d$reference$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/build/webpack/loaders/next-flight-loader/server-reference.js [app-rsc] (ecmascript)");
/**
 * Başvuru formu server action'ı (CONTRACT §3 `POST basvurular/`).
 *
 * Tarayıcı API'ye doğrudan istek atmaz; form bu action üzerinden sunucudan iletilir.
 * Gerçek istemci IP'si `X-Website-Client-IP` ile, site kimliği `X-Website-Token` ile gönderilir.
 *
 * Kullanım (client component):
 *   const [sonuc, gonder, bekliyor] = useActionState(basvuruGonder, null);
 *   <form action={gonder}> ... <input name="tip" type="hidden" value="pilot" /> ... </form>
 *
 * Form alan adları CONTRACT ile birebir: tip, ad_soyad, kurum, eposta, telefon, il, mesaj,
 * kvkk_onay (checkbox), kaynak_sayfa (hidden), website (honeypot — görünmez bırakın).
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/headers.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/env.ts [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$webpack$2f$loaders$2f$next$2d$flight$2d$loader$2f$action$2d$validate$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/build/webpack/loaders/next-flight-loader/action-validate.js [app-rsc] (ecmascript)");
;
;
;
const TIPLER = [
    "pilot",
    "sponsor",
    "genel"
];
const EPOSTA_DESENI = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const GENEL_HATA = "Başvurunuz şu anda iletilemedi. Lütfen biraz sonra tekrar deneyin veya bize e-posta ile ulaşın.";
function metin(fd, ad, max = 500) {
    const v = fd.get(ad);
    return typeof v === "string" ? v.trim().slice(0, max) : "";
}
function onayMi(fd, ad) {
    const v = fd.get(ad);
    return v === "on" || v === "true" || v === "1";
}
/** Gelen istekten istemci IP'si (proxy arkasında x-forwarded-for'un ilk öğesi). */ async function istemciIp() {
    const h = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$headers$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["headers"])();
    const xff = h.get("x-forwarded-for");
    const aday = (xff ? xff.split(",")[0] : h.get("x-real-ip") || "").trim();
    return /^[0-9a-fA-F:.]{3,45}$/.test(aday) ? aday : "";
}
/** İstemci tarafı ile aynı temel doğrulama (asıl doğrulama backend'dedir). */ function dogrula(g) {
    const h = {};
    if (!g.ad_soyad) h.ad_soyad = [
        "Ad soyad zorunludur."
    ];
    if (!g.eposta) h.eposta = [
        "E-posta zorunludur."
    ];
    else if (!EPOSTA_DESENI.test(g.eposta)) h.eposta = [
        "Geçerli bir e-posta adresi girin."
    ];
    if (g.telefon.length > 20) h.telefon = [
        "Telefon en fazla 20 karakter olabilir."
    ];
    if (g.mesaj.length > 2000) h.mesaj = [
        "Mesaj en fazla 2000 karakter olabilir."
    ];
    if (!g.kvkk_onay) h.kvkk_onay = [
        "Devam etmek için KVKK aydınlatma metnini onaylamanız gerekir."
    ];
    return h;
}
/** DRF hata gövdesini `{ alan: [mesaj] }` biçimine normalize eder. */ function hatalariNormalize(govde) {
    const hatalar = {};
    let genel = null;
    if (govde && typeof govde === "object" && !Array.isArray(govde)) {
        for (const [alan, deger] of Object.entries(govde)){
            const mesajlar = (Array.isArray(deger) ? deger : [
                deger
            ]).filter((m)=>typeof m === "string");
            if (!mesajlar.length) continue;
            if (alan === "non_field_errors" || alan === "detail") genel = mesajlar.join(" ");
            else hatalar[alan] = mesajlar;
        }
    }
    return {
        hatalar,
        genel
    };
}
async function basvuruGonder(_onceki, formData) {
    const tipHam = metin(formData, "tip", 20);
    const kaynak = metin(formData, "kaynak_sayfa", 200);
    const govde = {
        tip: TIPLER.includes(tipHam) ? tipHam : "genel",
        ad_soyad: metin(formData, "ad_soyad", 150),
        kurum: metin(formData, "kurum", 200),
        eposta: metin(formData, "eposta", 254),
        telefon: metin(formData, "telefon", 40),
        il: metin(formData, "il", 100),
        mesaj: metin(formData, "mesaj", 4000),
        kvkk_onay: onayMi(formData, "kvkk_onay"),
        kaynak_sayfa: kaynak.startsWith("/") ? kaynak : "/",
        website: metin(formData, "website", 200)
    };
    const hatalar = dogrula(govde);
    if (Object.keys(hatalar).length) {
        return {
            ok: false,
            hatalar,
            mesaj: "Lütfen işaretli alanları kontrol edin."
        };
    }
    if (__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["env"].mockApi) {
        return {
            ok: true,
            hatalar: {},
            mesaj: "Başvurunuz alındı (MOCK modu — kayıt oluşturulmadı)."
        };
    }
    let yanit;
    try {
        yanit = await fetch(`${__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["env"].apiInternalUrl}/api/website/public/basvurular/`, {
            method: "POST",
            cache: "no-store",
            signal: AbortSignal.timeout(10_000),
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
                "X-Website-Token": __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$env$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["env"].websiteServerToken,
                "X-Website-Client-IP": await istemciIp()
            },
            body: JSON.stringify(govde)
        });
    } catch (hata) {
        console.error("[e-isa basvuru] API'ye ulaşılamadı:", hata instanceof Error ? hata.message : hata);
        return {
            ok: false,
            hatalar: {},
            mesaj: GENEL_HATA
        };
    }
    if (yanit.status === 201 || yanit.ok) {
        return {
            ok: true,
            hatalar: {},
            mesaj: "Başvurunuz alındı."
        };
    }
    if (yanit.status === 429) {
        return {
            ok: false,
            hatalar: {},
            mesaj: "Kısa süre içinde çok fazla başvuru gönderildi. Lütfen bir süre sonra tekrar deneyin."
        };
    }
    if (yanit.status === 400) {
        let govdeJson = null;
        try {
            govdeJson = await yanit.json();
        } catch  {
        // gövde yoksa genel mesaj
        }
        const { hatalar: apiHatalari, genel } = hatalariNormalize(govdeJson);
        return {
            ok: false,
            hatalar: apiHatalari,
            mesaj: genel ?? "Lütfen işaretli alanları kontrol edin."
        };
    }
    console.error(`[e-isa basvuru] beklenmeyen API yanıtı: ${yanit.status}`);
    return {
        ok: false,
        hatalar: {},
        mesaj: GENEL_HATA
    };
}
;
(0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$webpack$2f$loaders$2f$next$2d$flight$2d$loader$2f$action$2d$validate$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ensureServerEntryExports"])([
    basvuruGonder
]);
(0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$webpack$2f$loaders$2f$next$2d$flight$2d$loader$2f$server$2d$reference$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["registerServerReference"])(basvuruGonder, "60d94374f20878874fb67ce4e3ee2857f4d28230ac", null);
}),
];

//# sourceMappingURL=_1xjiuz67ijmk_._.js.map