import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError, NetworkError, type WritingSubmissionSummary, type WritingTask } from "@/shared/api";
import WritingTaskPage from "./[id]/page";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "3" }), useRouter: () => ({ push }) }));
vi.mock("@/shared/auth", () => ({
  useRequireAuth: () => ({ token: "token", ready: true }),
  useAuth: () => ({ username: "ann" }),
}));
vi.mock("@/shared/api", async (original) => ({ ...await original<object>(), api: {
  getWritingTask: vi.fn(), getWritingQuota: vi.fn(), submitWriting: vi.fn(), listWritingSubmissions: vi.fn(),
} }));

const task = { id: 3, task_type: 2, title: "Essay", prompt: "Discuss.", min_words: 250, duration_minutes: 40,
  image_url: null, visual_data: null } as unknown as WritingTask;
const summary = (id: number, status = "pending"): WritingSubmissionSummary => ({ id, task_id: 3, task_title: "Essay",
  word_count: 5, status, band: null, created_at: new Date().toISOString() });

async function openAndSubmit() {
  render(<WritingTaskPage />);
  fireEvent.change(await screen.findByLabelText("Your answer"), { target: { value: "An essay about cities." } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
}

beforeEach(() => {
  vi.mocked(api.getWritingTask).mockResolvedValue(task);
  vi.mocked(api.getWritingQuota).mockRejectedValue(new Error("no quota"));
  vi.mocked(api.submitWriting).mockRejectedValue(new NetworkError("timeout"));
});
afterEach(() => { vi.resetAllMocks(); localStorage.clear(); });

it("opens the result page when a timed-out submit did reach the server", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValueOnce([summary(10, "graded")]).mockResolvedValueOnce([summary(11), summary(10, "graded")]);
  await openAndSubmit();
  expect(api.submitWriting).toHaveBeenCalledTimes(1);
  expect(push).toHaveBeenCalledWith("/writing/result/11");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("opens the result page when the server says the essay is already being graded", async () => {
  vi.mocked(api.submitWriting).mockRejectedValue(new ApiError(409, "This essay is already being graded."));
  vi.mocked(api.listWritingSubmissions).mockResolvedValueOnce([]).mockResolvedValueOnce([summary(11)]);
  await openAndSubmit();
  expect(push).toHaveBeenCalledWith("/writing/result/11");
});

it("offers a retry only after confirming the essay was not received", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([summary(10, "graded")]);
  await openAndSubmit();
  expect(push).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toHaveTextContent(/try again/i);
  expect(screen.getByRole("button", { name: "Submit" })).toBeEnabled();
});

it("blocks a blind resubmit while the outcome is unknown, then recovers on a status check", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValueOnce([]).mockRejectedValueOnce(new NetworkError("network"));
  await openAndSubmit();
  expect(screen.getByRole("alert")).toHaveTextContent(/could not confirm/i);
  expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();
  vi.mocked(api.listWritingSubmissions).mockResolvedValueOnce([summary(12)]);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Check submission status" })); });
  expect(api.submitWriting).toHaveBeenCalledTimes(1);
  expect(push).toHaveBeenCalledWith("/writing/result/12");
});

it("does not look anything up for an ordinary rejection", async () => {
  vi.mocked(api.submitWriting).mockRejectedValue(new ApiError(429, "Daily limit reached."));
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([]);
  await openAndSubmit();
  expect(api.listWritingSubmissions).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("alert")).toHaveTextContent("Daily limit reached.");
});
