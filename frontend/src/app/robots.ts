import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://testora.studio";

// Only the public pages are indexable; everything else needs a signed-in user.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: ["/", "/login", "/register"], disallow: ["/history", "/profile", "/analytics"] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
