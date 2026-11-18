import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SESSION_HINT_CLASS, SESSION_HINT_SCRIPT } from "@/shared/api";
import { HomeGate } from "./HomeGate";

const auth = vi.hoisted(() => ({ token: null as string | null, username: null as string | null, ready: false }));
vi.mock("@/shared/auth", () => ({ useAuth: () => auth }));
vi.mock("@/widgets/coach-dashboard", () => ({ CoachDashboard: () => <p>Dashboard</p> }));

const runHintScript = () => new Function(SESSION_HINT_SCRIPT)();

afterEach(() => {
  Object.assign(auth, { token: null, username: null, ready: false });
  document.documentElement.classList.remove(SESSION_HINT_CLASS);
  sessionStorage.clear();
});

it("marks the page only when the tab holds a session token", () => {
  runHintScript();
  expect(document.documentElement).not.toHaveClass(SESSION_HINT_CLASS);
  sessionStorage.setItem("testora.auth.token", "jwt");
  runHintScript();
  expect(document.documentElement).toHaveClass(SESSION_HINT_CLASS);
});

it("renders the landing markup before auth is known, as on the server", () => {
  document.documentElement.classList.add(SESSION_HINT_CLASS);
  render(<HomeGate landing={<p>Landing</p>} />);
  expect(screen.getByText("Landing")).toBeInTheDocument();
  // Still marked: CSS keeps the landing hidden until auth resolves.
  expect(document.documentElement).toHaveClass(SESSION_HINT_CLASS);
});

it("reveals the landing once the tab turns out to be signed out", () => {
  document.documentElement.classList.add(SESSION_HINT_CLASS);
  auth.ready = true;
  render(<HomeGate landing={<p>Landing</p>} />);
  expect(screen.getByText("Landing")).toBeInTheDocument();
  expect(document.documentElement).not.toHaveClass(SESSION_HINT_CLASS);
});

it("shows the dashboard to a signed-in user", () => {
  Object.assign(auth, { token: "jwt", username: "ann", ready: true });
  render(<HomeGate landing={<p>Landing</p>} />);
  expect(screen.getByText("Dashboard")).toBeInTheDocument();
  expect(screen.queryByText("Landing")).not.toBeInTheDocument();
});
