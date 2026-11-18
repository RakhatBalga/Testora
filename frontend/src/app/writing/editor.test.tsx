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
afterEach(() => { vi.useRealTimers(); vi.resetAllMocks(); localStorage.clear(); });

const DRAFT = "testora.writing.draft.ann.3";
const KEY = `${DRAFT}-submission-key`;

it("autosaves the draft and restores it after a reload", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([]);
  vi.useFakeTimers();
  const view = render(<WritingTaskPage />);
  await act(async () => {});
  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "Cities grow" } });
  expect(localStorage.getItem(DRAFT)).toBeNull();
  await act(async () => { await vi.advanceTimersByTimeAsync(500); });
  expect(localStorage.getItem(DRAFT)).toBe("Cities grow");
  view.unmount();

  render(<WritingTaskPage />);
  await act(async () => {});
  expect(screen.getByLabelText("Your answer")).toHaveValue("Cities grow");
  expect(screen.getByText("Your saved draft was restored.")).toBeInTheDocument();
  expect(screen.getByText("2 / 250 words")).toBeInTheDocument();
  localStorage.setItem(KEY, JSON.stringify({ key: "stale-key-1", text: "Cities grow" }));

  fireEvent.click(screen.getByRole("button", { name: /Discard draft/ }));
  expect(screen.getByLabelText("Your answer")).toHaveValue("");
  expect(localStorage.getItem(DRAFT)).toBeNull();
  expect(localStorage.getItem(KEY)).toBeNull();
});

it("submits the essay, opens its result and clears the draft and key", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([]);
  vi.mocked(api.submitWriting).mockResolvedValue({ id: 21 } as Awaited<ReturnType<typeof api.submitWriting>>);
  vi.useFakeTimers();
  render(<WritingTaskPage />);
  await act(async () => {});
  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "  An essay about cities.  " } });
  await act(async () => { await vi.advanceTimersByTimeAsync(500); });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
  expect(api.submitWriting).toHaveBeenCalledWith(3, "An essay about cities.", expect.stringMatching(/^[A-Za-z0-9._:-]{8,80}$/));
  expect(JSON.parse(localStorage.getItem(KEY) ?? "null")).toMatchObject({ text: "An essay about cities." });
  // The review overlay stays up for a moment before the result opens.
  expect(screen.getByRole("status", { name: /reviewing your writing/i })).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
  await act(async () => { await vi.advanceTimersByTimeAsync(7_000); });
  expect(push).toHaveBeenCalledWith("/writing/result/21");
  expect(localStorage.getItem(DRAFT)).toBeNull();
  expect(localStorage.getItem(KEY)).toBeNull();
});

it("sends a new submission key when the essay was edited after a failed submit", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([]);
  render(<WritingTaskPage />);
  fireEvent.change(await screen.findByLabelText("Your answer"), { target: { value: "An essay about cities." } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "An essay about cities, improved." } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
  // Unchanged again: the second key is reused, not the first.
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
  const calls = vi.mocked(api.submitWriting).mock.calls;
  expect(calls.map((call) => call[1])).toEqual(["An essay about cities.", "An essay about cities, improved.", "An essay about cities, improved."]);
  expect(calls[1][2]).not.toBe(calls[0][2]);
  expect(calls[2][2]).toBe(calls[1][2]);
});

it("reuses the same submission key for an unchanged retry, also after a reload", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([]);
  const view = render(<WritingTaskPage />);
  fireEvent.change(await screen.findByLabelText("Your answer"), { target: { value: "An essay about cities." } });
  await act(async () => { await new Promise((resolve) => setTimeout(resolve, 550)); });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
  view.unmount();

  render(<WritingTaskPage />);
  await screen.findByText("Your saved draft was restored.");
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit" })); });
  const keys = vi.mocked(api.submitWriting).mock.calls.map((call) => call[2]);
  expect(keys).toHaveLength(3);
  expect(keys[0]).toMatch(/^[A-Za-z0-9._:-]{8,80}$/);
  expect(new Set(keys).size).toBe(1);
});

it("disables submit when the free reviews are used up", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([]);
  vi.mocked(api.getWritingQuota).mockResolvedValue({ limit: 3, used: 3, remaining: 0, exempt: false } as Awaited<ReturnType<typeof api.getWritingQuota>>);
  render(<WritingTaskPage />);
  fireEvent.change(await screen.findByLabelText("Your answer"), { target: { value: "An essay about cities." } });
  expect(await screen.findByText(/used your 3 free AI reviews/)).toBeInTheDocument();
  const submit = screen.getByRole("button", { name: /Limit reached/ });
  expect(submit).toBeDisabled();
  fireEvent.click(submit);
  expect(api.submitWriting).not.toHaveBeenCalled();
});

it("keeps submit available for an account exempt from the quota", async () => {
  vi.mocked(api.listWritingSubmissions).mockResolvedValue([]);
  vi.mocked(api.getWritingQuota).mockResolvedValue({ limit: 3, used: 9, remaining: 0, exempt: true } as Awaited<ReturnType<typeof api.getWritingQuota>>);
  render(<WritingTaskPage />);
  fireEvent.change(await screen.findByLabelText("Your answer"), { target: { value: "An essay about cities." } });
  await act(async () => {});
  expect(screen.getByRole("button", { name: "Submit" })).toBeEnabled();
});

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
