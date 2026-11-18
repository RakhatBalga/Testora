import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { SubmitConfirm } from "./SubmitConfirm";

const props = { answered: 3, total: 4, submitting: false, onConfirm: vi.fn(), onCancel: vi.fn() };

it("is a labelled modal dialog that takes focus and keeps Tab inside", () => {
  render(<SubmitConfirm {...props} open />);
  expect(screen.getByRole("dialog", { name: "Submit your answers?" })).toHaveAttribute("aria-modal", "true");
  const keep = screen.getByRole("button", { name: "Keep working" });
  const submit = screen.getByRole("button", { name: "Submit now" });
  expect(keep).toHaveFocus();
  fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
  expect(submit).toHaveFocus();
  fireEvent.keyDown(document, { key: "Tab" });
  expect(keep).toHaveFocus();
});

it("closes on Escape, but not while submitting, and restores focus", () => {
  const onCancel = vi.fn();
  const opener = document.createElement("button");
  document.body.append(opener);
  opener.focus();
  const view = render(<SubmitConfirm {...props} onCancel={onCancel} submitting open />);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(onCancel).not.toHaveBeenCalled();
  view.rerender(<SubmitConfirm {...props} onCancel={onCancel} open />);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(onCancel).toHaveBeenCalledTimes(1);
  view.rerender(<SubmitConfirm {...props} onCancel={onCancel} open={false} />);
  expect(opener).toHaveFocus();
  opener.remove();
});
