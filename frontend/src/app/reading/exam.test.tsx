import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, NetworkError, type AttemptResult, type TestDetail } from "@/shared/api";
import ReadingPage from "./[id]/page";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "4" }), useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/shared/auth", () => ({
  useRequireAuth: () => ({ token: "token", ready: true }),
  useAuth: () => ({ username: "ann" }),
}));
vi.mock("@/shared/api", async (original) => ({ ...await original<object>(), api: {
  getTest: vi.fn(), getAttempt: vi.fn(), submit: vi.fn(),
} }));
// The exam chrome is what is under test; the passage/question widgets are not.
vi.mock("@/features/reading-session", () => ({
  ReadingPassage: () => null, PassageAnnotator: () => null, ReadingPassageNav: () => null, ReadingTimer: () => null,
  ReadingQuestions: ({ onAnswer }: { onAnswer: (id: number, value: string) => void }) => (
    <button type="button" onClick={() => onAnswer(1, "TRUE")}>Answer question</button>
  ),
  ReadingReviewSplit: ({ result }: { result: AttemptResult }) => <p>Review of attempt {result.id}</p>,
}));

const test: TestDetail = {
  id: 4, title: "Reading test", test_type: "reading", description: null, duration_minutes: 1, difficulty: null,
  question_count: 1,
  sections: [{ id: 1, order: 1, title: "Passage 1", instructions: null, passage: "Text", audio_url: null,
    questions: [{ id: 1, order: 1, text: "Q1", question_type: "true_false_not_given", options: null, word_limit: null, evidence: null }] }],
} as unknown as TestDetail;
const attempt = (id: number) => ({ id, test_id: 4, test_type: "reading" }) as AttemptResult;

beforeEach(() => {
  vi.mocked(api.getTest).mockResolvedValue(test);
  vi.mocked(api.getAttempt).mockImplementation(async (id) => attempt(id));
  vi.spyOn(window, "confirm").mockReturnValue(true);
  window.scrollTo = vi.fn();
});
afterEach(() => {
  vi.useRealTimers();
  vi.resetAllMocks();
  vi.restoreAllMocks();
  localStorage.clear();
  window.history.replaceState(null, "", "/");
});

it("submits the answers and shows the review", async () => {
  vi.mocked(api.submit).mockResolvedValue(attempt(70));
  render(<ReadingPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Answer question" }));
  expect(JSON.parse(localStorage.getItem("reading-ann-4-answers") ?? "{}")).toEqual({ "1": "TRUE" });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /^Submit$/ })); });
  expect(window.confirm).toHaveBeenCalledWith("Submit this Reading test?");
  expect(api.submit).toHaveBeenCalledWith(4, [{ question_id: 1, answer: "TRUE" }], expect.any(Number), expect.any(String));
  expect(screen.getByText("Review of attempt 70")).toBeInTheDocument();
  expect(localStorage.getItem("reading-ann-4-result")).toBe("70");
  expect(localStorage.getItem("reading-ann-4-answers")).toBeNull();
});

it("does not submit when the confirmation is declined", async () => {
  vi.mocked(window.confirm).mockReturnValue(false);
  render(<ReadingPage />);
  await screen.findByRole("button", { name: "Answer question" });
  fireEvent.click(screen.getByRole("button", { name: /^Submit$/ }));
  expect(window.confirm).toHaveBeenCalledWith("Submit this Reading test? 1 question is unanswered.");
  expect(api.submit).not.toHaveBeenCalled();
});

it("retries a failed submit with the same key, also after a reload", async () => {
  vi.mocked(api.submit).mockRejectedValue(new NetworkError("timeout"));
  const view = render(<ReadingPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Answer question" }));
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /^Submit$/ })); });
  // The exam stays on screen with the answers kept and a way to retry.
  expect(screen.getByRole("alert")).toHaveTextContent(/Your answers are saved on this device/);
  expect(screen.getByRole("button", { name: "Answer question" })).toBeInTheDocument();
  expect(JSON.parse(localStorage.getItem("reading-ann-4-answers") ?? "{}")).toEqual({ "1": "TRUE" });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Retry submit" })); });
  view.unmount();

  // Reload: the draft and its key come back from storage.
  vi.mocked(api.submit).mockResolvedValue(attempt(77));
  render(<ReadingPage />);
  await screen.findByRole("button", { name: "Answer question" });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /^Submit$/ })); });

  const keys = vi.mocked(api.submit).mock.calls.map((call) => call[3]);
  expect(keys).toHaveLength(3);
  expect(keys[0]).toMatch(/^[A-Za-z0-9._:-]{8,80}$/);
  expect(new Set(keys).size).toBe(1);
  expect(screen.getByText("Review of attempt 77")).toBeInTheDocument();
  // The saved attempt closes the key: the next attempt gets a new one.
  expect(localStorage.getItem("reading-ann-4-submission-key")).toBeNull();
});

it("starts a retake once: a reload afterwards keeps the new result", async () => {
  localStorage.setItem("reading-ann-4-result", "50");
  window.history.replaceState(null, "", "/reading/4?retake=1");
  vi.mocked(api.submit).mockResolvedValue(attempt(51));
  const view = render(<ReadingPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Answer question" }));
  expect(window.location.search).toBe("");
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /^Submit$/ })); });
  view.unmount();

  render(<ReadingPage />);
  expect(await screen.findByText("Review of attempt 51")).toBeInTheDocument();
  expect(api.submit).toHaveBeenCalledTimes(1);
});

it("does not file a blank attempt when the clock runs out with nothing answered", async () => {
  vi.useFakeTimers();
  render(<ReadingPage />);
  await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
  await act(async () => { await vi.advanceTimersByTimeAsync(61_000); });
  expect(screen.getByText("Time is up")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Restart test" })).toBeInTheDocument();
  expect(api.submit).not.toHaveBeenCalled();
});

it("still submits at zero when something was answered", async () => {
  vi.useFakeTimers();
  vi.mocked(api.submit).mockResolvedValue(attempt(60));
  render(<ReadingPage />);
  await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
  fireEvent.click(screen.getByRole("button", { name: "Answer question" }));
  await act(async () => { await vi.advanceTimersByTimeAsync(61_000); });
  expect(api.submit).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Review of attempt 60")).toBeInTheDocument();
});
