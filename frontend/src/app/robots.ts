import type { MetadataRoute } from "next";
import { routes } from "@/shared/config";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://testora.studio";

// Only the public pages are indexable; everything else needs a signed-in user.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: [routes.dashboard(), routes.login(), routes.register()], disallow: [routes.history(), routes.profile(), routes.analytics()] },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
