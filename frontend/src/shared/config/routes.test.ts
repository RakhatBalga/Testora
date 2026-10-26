import { existsSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { describe, expect, it } from "vitest";
import nextConfig from "../../../next.config";
import patterns from "./routes.json";
import { resultHref, routes } from "./routes";

const APP_DIR = join(__dirname, "../../app");

function pageFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return pageFiles(full);
    return name === "page.tsx" ? [full] : [];
  });
}

/** "/reading/[id]" style patterns of every page under src/app ("{id}" in routes.json). */
const pagePatterns = pageFiles(APP_DIR).map((file) => {
  const dir = relative(APP_DIR, file).split(sep).slice(0, -1);
  return "/" + dir.map((seg) => (seg.startsWith("[") ? "{id}" : seg)).join("/");
});

/** Does a concrete path (no query) match a page pattern? Static segments win over dynamic ones. */
function matchesPage(path: string): boolean {
  const parts = path.split("/").filter(Boolean);
  return pagePatterns.some((pattern) => {
    const pp = pattern.split("/").filter(Boolean);
    return pp.length === parts.length && pp.every((seg, i) => seg === "{id}" || seg === parts[i]);
  });
}

const pathOf = (href: string) => href.split("?")[0];

// Every builder, called with sample arguments. A new builder must be added here.
const samples: Record<string, string> = {
  dashboard: routes.dashboard(),
  login: routes.login(),
  register: routes.register(),
  googleCallback: routes.googleCallback(),
  practice: routes.practice(),
  studyPlan: routes.studyPlan(),
  mistakes: routes.mistakes(),
  "mistakes(skill)": routes.mistakes({ skill: "writing" }),
  vocabulary: routes.vocabulary(),
  history: routes.history(),
  historyCompare: routes.historyCompare("a1", "b2"),
  analytics: routes.analytics(),
  profile: routes.profile(),
  ...Object.fromEntries(
    (["reading", "listening", "writing", "speaking"] as const).flatMap((skill) => [
      [`${skill}.library`, routes[skill].library()],
      [`${skill}.exam`, routes[skill].exam(7)],
      [`${skill}.result`, routes[skill].result(7)],
    ]),
  ),
  "reading.retake": routes.reading.retake(7),
  "listening.retake": routes.listening.retake(7),
  "writing.library(task)": routes.writing.library(2),
};

function leafCount(obj: object): number {
  return Object.values(obj).reduce<number>((n, v) => n + (typeof v === "function" ? 1 : leafCount(v as object)), 0);
}

describe("route map", () => {
  it("has a sample for every builder", () => {
    // 12 top-level + 3 skills x 3 (+ retake x2) + writing/speaking/reading/listening
    expect(Object.keys(samples).length).toBeGreaterThanOrEqual(leafCount(routes));
  });

  it.each(Object.entries(samples))("%s resolves to an existing page", (_name, href) => {
    expect(matchesPage(pathOf(href)), `${href} has no page in src/app`).toBe(true);
  });

  it("follows the same scheme for all four skills", () => {
    for (const skill of ["reading", "listening", "writing", "speaking"] as const) {
      expect(routes[skill].library()).toBe(`/${skill}`);
      expect(routes[skill].exam(3)).toBe(`/${skill}/3`);
      expect(routes[skill].result(3)).toBe(`/${skill}/result/3`);
    }
    expect(resultHref("reading", 5)).toBe("/reading/result/5");
  });

  it("routes.json lists exactly the pages in src/app", () => {
    expect([...patterns.patterns].sort()).toEqual([...new Set(pagePatterns)].sort());
  });
});

describe("redirects", () => {
  it("point to existing pages", async () => {
    const redirects = await nextConfig.redirects!();
    expect(redirects.length).toBeGreaterThan(0);
    for (const r of redirects) {
      expect(matchesPage(r.destination.replace(/:\w+/g, "1")), `${r.source} -> ${r.destination}`).toBe(true);
    }
  });

  it("keeps the old URLs alive and removes their pages", async () => {
    const map = Object.fromEntries((await nextConfig.redirects!()).map((r) => [r.source, r.destination]));
    expect(map["/tests/reading"]).toBe("/reading");
    expect(map["/tests/listening"]).toBe("/listening");
    expect(map["/result/:id"]).toBe("/reading/result/:id");
    expect(map["/mock-tests"]).toBe("/practice");
    for (const dir of ["tests", "result", "mock-tests", "test"]) {
      expect(existsSync(join(APP_DIR, dir))).toBe(false);
    }
  });
});
