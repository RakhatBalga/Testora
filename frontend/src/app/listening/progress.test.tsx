import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, type ListeningTest } from "@/shared/api";
import ListeningPage from "./[id]/page";
import ListeningLibraryPage from "./page";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useParams: () => ({ id: "1" }), useRouter: () => ({ push }) }));
vi.mock("@/shared/auth", () => ({ useRequireAuth: () => ({ token: "token", ready: true }) }));
vi.mock("@/shared/api", async (original) => ({ ...await original<object>(), api: {
  getListeningTest: vi.fn(), getListeningProgress: vi.fn(), saveListeningProgress: vi.fn(),
  submitListening: vi.fn(), listListeningTests: vi.fn(), listAttempts: vi.fn(),
} }));
const test: ListeningTest = {
  id: 1, title: "Listening practice", description: null, duration_minutes: 30,
  difficulty: null, question_count: 4, content_version: "1.0.1", calibration_status: "provisional",
  authorship: "original", schema_version: "testora.listening-public.v1", intro_notice: "",
  sections: Array.from({ length: 4 }, (_, i) => ({ id: i + 1, order: i + 1,
    title: `Section ${i + 1}`, instructions: null, audio_url: null, audio_start: i * 100,
    audio_end: (i + 1) * 100, map_asset: null,
    questions: [{ id: i + 1, order: i + 1, text: `Question ${i + 1}`, question_type: "short_answer", options: null, word_limit: 2 }],
  })),
};
beforeEach(() => {
  vi.mocked(api.getListeningTest).mockResolvedValue(test);
  vi.mocked(api.getListeningProgress).mockResolvedValue(null);
  vi.mocked(api.saveListeningProgress).mockResolvedValue({ content_version: "1.0.1", mode: "practice", answers: {}, current_section: 0, audio_position: 0, max_audio_position: 0, status: "in_progress", updated_at: new Date().toISOString() });
  vi.mocked(api.submitListening).mockResolvedValue({ attempt_id: 42 } as Awaited<ReturnType<typeof api.submitListening>>);
  vi.mocked(api.listListeningTests).mockResolvedValue([test]);
  vi.mocked(api.listAttempts).mockResolvedValue([]);
});
afterEach(() => { vi.useRealTimers(); vi.resetAllMocks(); localStorage.clear(); });

it("restores the last answer after leaving before the 500ms autosave", async () => {
  vi.useFakeTimers();
  let view = render(<ListeningPage />);
  await act(async () => {});
  fireEvent.change(screen.getByPlaceholderText("Type your answer"), { target: { value: "Hartley" } });
  view.unmount();
  expect(api.saveListeningProgress).not.toHaveBeenCalled();
  view = render(<ListeningPage />);
  await act(async () => {});
  expect(screen.getByPlaceholderText("Type your answer")).toHaveValue("Hartley");
  view.unmount();
});

it("restores a saved section and its answers from the server", async () => {
  vi.mocked(api.getListeningProgress).mockResolvedValue({ content_version: "1.0.1", mode: "practice", answers: { "3": "library" }, current_section: 2, audio_position: 240, max_audio_position: 250, status: "in_progress", updated_at: new Date().toISOString() });
  render(<ListeningPage />);
  expect(await screen.findByPlaceholderText("Type your answer")).toHaveValue("library");
  expect(screen.getByText(/Section 3 of 4/)).toBeInTheDocument();
});

it("shows a progress load failure instead of an endless skeleton", async () => {
  vi.mocked(api.getListeningProgress).mockRejectedValue(new Error("Progress unavailable"));
  render(<ListeningPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Progress unavailable");
  expect(api.saveListeningProgress).not.toHaveBeenCalled();
});

it("submits the latest answers, clears recovery data and does not autosave afterward", async () => {
  vi.useFakeTimers();
  const view = render(<ListeningPage />);
  await act(async () => {});
  fireEvent.change(screen.getByPlaceholderText("Type your answer"), { target: { value: "Hartley" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Submit now" })); });
  expect(api.submitListening).toHaveBeenCalledWith(1, expect.objectContaining({ answers: expect.arrayContaining([{ question_id: 1, answer: "Hartley" }]) }));
  expect(push).toHaveBeenCalledWith("/listening/result/42");
  await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
  expect(api.saveListeningProgress).not.toHaveBeenCalled();
  expect(Object.keys(localStorage).filter((key) => key.endsWith("-draft"))).toEqual([]);
  view.unmount();
});

it("offers Continue for server progress even when an older attempt is completed", async () => {
  vi.mocked(api.getListeningProgress).mockResolvedValue({ content_version: "1.0.1", mode: "practice", answers: { "1": "Hartley" }, current_section: 1, audio_position: 120, max_audio_position: 120, status: "in_progress", updated_at: new Date().toISOString() });
  vi.mocked(api.listAttempts).mockResolvedValue([{ id: 42, test_id: 1, test_title: test.title, test_type: "listening", score: 1, total: 4, band: 3, created_at: "2026-10-17T10:00:00Z" }]);
  render(<ListeningLibraryPage />);
  expect(await screen.findByText("Continue last session")).toBeInTheDocument();
  expect(screen.getByText(/1 of 4 questions answered/)).toBeInTheDocument();
});

