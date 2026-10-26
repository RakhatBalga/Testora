/** Where to take (or retake) a test, by its type. Every type has its own exam screen. */
export function examHref(testType: string, testId: number, options: { retake?: boolean } = {}): string {
  const suffix = options.retake ? "?retake=1" : "";
  if (testType === "listening") return `/listening/${testId}${suffix}`;
  if (testType === "reading") return `/reading/${testId}${suffix}`;
  // Unknown/legacy type: send the user to the library rather than a dead route.
  return "/tests/reading";
}
