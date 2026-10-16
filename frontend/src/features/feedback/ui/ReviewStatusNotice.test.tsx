import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ReviewStatusNotice, reviewState } from "./ReviewStatusNotice";

it.each([
  [{ status: "pending", band: null, feedback: { summary: "old failure" } }, "pending"],
  [{ status: "failed", band: null, feedback: null }, "failed"],
  [{ band: null, feedback: null }, "pending"],
  [{ band: null, feedback: { summary: "provider failed" } }, "failed"],
  [{ band: 0, feedback: { band: 0 } }, "graded"],
])("does not mistake an unfinished review for a grade or an old failure", (submission, expected) => {
  expect(reviewState(submission)).toBe(expected);
});

it("explains an unfinished review and refreshes only when requested", async () => {
  const refresh = vi.fn().mockResolvedValue(undefined);
  render(<ReviewStatusNotice state="pending" onRefresh={refresh} />);
  expect(screen.getByRole("status")).toHaveTextContent("may have been interrupted");
  expect(refresh).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Check review status" }));
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(screen.getByRole("button")).toBeEnabled());
});

it("shows refresh errors without losing the saved-response notice", async () => {
  render(<ReviewStatusNotice state="pending" onRefresh={vi.fn().mockRejectedValue(new Error("Network unavailable"))} />);
  fireEvent.click(screen.getByRole("button"));
  expect(await screen.findByRole("alert")).toHaveTextContent("Network unavailable");
  expect(screen.getByRole("status")).toHaveTextContent("Your response is saved");
});
