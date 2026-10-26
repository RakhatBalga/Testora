import { routes } from "@/shared/config";

/** Where to take (or retake) a test, by its type. Every type has its own exam screen. */
export function examHref(testType: string, testId: number, options: { retake?: boolean } = {}): string {
  if (testType === "listening") return options.retake ? routes.listening.retake(testId) : routes.listening.exam(testId);
  if (testType === "reading") return options.retake ? routes.reading.retake(testId) : routes.reading.exam(testId);
  // Unknown/legacy type: send the user to the library rather than a dead route.
  return routes.reading.library();
}
