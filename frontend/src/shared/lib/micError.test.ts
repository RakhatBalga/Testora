import { expect, it } from "vitest";
import { micErrorMessage } from "./micError";

it("maps permission denial to settings guidance, not the raw browser text", () => {
  const raw = new DOMException("The request is not allowed by the user agent", "NotAllowedError");
  const message = micErrorMessage(raw);
  expect(message).toContain("Microphone access is blocked");
  expect(message).not.toContain("user agent");
});

it("maps missing and busy devices and falls back generically", () => {
  expect(micErrorMessage(new DOMException("x", "NotFoundError"))).toContain("No microphone");
  expect(micErrorMessage(new DOMException("x", "NotReadableError"))).toContain("in use");
  expect(micErrorMessage("weird")).toContain("Could not start recording");
});
