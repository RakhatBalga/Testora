/**
 * The one map of internal page URLs. Every `href`, `router.push` and
 * `redirect` in the app builds its target here; the backend mirrors it in
 * `app/application/frontend_routes.py`. Tests check each builder against an
 * existing page in `src/app` and against `routes.json`.
 *
 * Scheme, identical for every skill:
 *   library  /<skill>
 *   exam     /<skill>/<id>
 *   result   /<skill>/result/<id>
 */

const skillRoutes = (skill: string) => ({
  library: () => `/${skill}`,
  exam: (id: number | string) => `/${skill}/${id}`,
  result: (id: number | string) => `/${skill}/result/${id}`,
});

export const routes = {
  dashboard: () => "/",
  login: () => "/login",
  register: () => "/register",
  googleCallback: () => "/auth/google/callback",
  practice: () => "/practice",
  studyPlan: () => "/study-plan",
  mistakes: (options: { skill?: string } = {}) => (options.skill ? `/mistakes?skill=${options.skill}` : "/mistakes"),
  vocabulary: () => "/vocabulary",
  history: () => "/history",
  historyCompare: (a: string, b: string) => `/history/compare?a=${a}&b=${b}`,
  analytics: () => "/analytics",
  profile: () => "/profile",

  reading: {
    ...skillRoutes("reading"),
    /** Starting a fresh attempt: forgets the stored result of the previous one. */
    retake: (id: number | string) => `/reading/${id}?retake=1`,
  },
  listening: {
    ...skillRoutes("listening"),
    retake: (id: number | string) => `/listening/${id}?retake=1`,
  },
  writing: {
    ...skillRoutes("writing"),
    /** Library filtered by task type (1 or 2); no argument = all tasks. */
    library: (taskType?: number | null) => (taskType ? `/writing?task=${taskType}` : "/writing"),
  },
  speaking: skillRoutes("speaking"),
} as const;

export type SkillName = "reading" | "listening" | "writing" | "speaking";

/** Result page of a graded item, by skill. */
export function resultHref(skill: string, id: number | string): string {
  const group = routes[skill as SkillName];
  return group ? group.result(id) : routes.practice();
}
