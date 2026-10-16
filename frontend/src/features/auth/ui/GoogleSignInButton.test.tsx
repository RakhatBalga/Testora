import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import GoogleSignInButton from "./GoogleSignInButton";
import { api } from "@/shared/api";

vi.mock("@/shared/api", () => ({ api: { googleStart: vi.fn() } }));

afterEach(() => { vi.unstubAllEnvs(); vi.clearAllMocks(); sessionStorage.clear(); });

it("starts only one flow for clicks in the same event batch and allows retry after failure", async () => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "test-client");
  let reject!: (error: Error) => void;
  vi.mocked(api.googleStart).mockImplementation(() => new Promise((_, fail) => { reject = fail; }));
  render(<GoogleSignInButton />);
  const button = screen.getByRole("button");
  act(() => {
    fireEvent.click(button);
    fireEvent.click(button);
  });
  expect(api.googleStart).toHaveBeenCalledTimes(1);
  expect(button).toBeDisabled();
  const firstState = vi.mocked(api.googleStart).mock.calls[0][0];
  await act(async () => reject(new Error("Please try again.")));
  expect(screen.getByRole("alert")).toHaveTextContent("Please try again.");
  expect(button).toBeEnabled();
  fireEvent.click(button);
  expect(api.googleStart).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api.googleStart).mock.calls[1][0]).not.toBe(firstState);
  await act(async () => reject(new Error("Please try again.")));
});

it("does not start a disabled sign-in flow", () => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "test-client");
  render(<GoogleSignInButton disabled />);
  fireEvent.click(screen.getByRole("button"));
  expect(api.googleStart).not.toHaveBeenCalled();
});
