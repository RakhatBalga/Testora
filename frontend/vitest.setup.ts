import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Unmount any React trees a test rendered so DOM state never leaks between tests.
afterEach(() => {
  cleanup();
});
