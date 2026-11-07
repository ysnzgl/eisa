import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/api";

// SITE_URL çalışma zamanında okunmalı (Docker imajı tek kez build edilir).
export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/api/"] }],
    sitemap: siteUrl("/sitemap.xml"),
  };
}
