import type { MetadataRoute } from "next";
import { routes } from "@/shared/config";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://testora.studio";

export default function sitemap(): MetadataRoute.Sitemap {
  return [routes.dashboard(), routes.login(), routes.register()].map((path) => ({
    url: `${SITE_URL}${path}`,
    changeFrequency: path === "/" ? "weekly" : "monthly",
    priority: path === "/" ? 1 : 0.5,
  }));
}
