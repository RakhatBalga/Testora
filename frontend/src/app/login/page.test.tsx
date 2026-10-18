import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import LoginPage from "./page";

const { login, push } = vi.hoisted(() => ({ login: vi.fn(), push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/shared/auth", () => ({ useAuth: () => ({ login }) }));
vi.mock("@/features/auth", async (importOriginal) => ({
  ...await importOriginal<object>(),
  AuthShell: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  GoogleSignInButton: () => null,
}));

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it("releases the button after timeout and allows a successful manual retry", async () => {
  vi.useFakeTimers();
  const fetchMock = vi.fn((_url, options: RequestInit) => new Promise((_, reject) => {
    options.signal!.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
  }));
  vi.stubGlobal("fetch", fetchMock);
  render(<LoginPage />);
  fireEvent.change(screen.getByLabelText("Email or username"), { target: { value: "user" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(screen.getByRole("button", { name: "Signing in..." })).toBeDisabled();
  await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
  expect(screen.getByRole("alert")).toHaveTextContent("Sign-in is taking too long.");
  expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(login).not.toHaveBeenCalled();
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "token", token_type: "bearer" })));
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Sign in" })); });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(login).toHaveBeenCalledWith("token", "user");
  expect(push).toHaveBeenCalledWith("/");
});
