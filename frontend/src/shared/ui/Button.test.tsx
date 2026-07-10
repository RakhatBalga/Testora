import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its label and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Grade my essay</Button>);

    await userEvent.click(screen.getByRole("button", { name: "Grade my essay" }));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Submit
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Submit" });
    expect(button).toBeDisabled();
    await userEvent.click(button);

    expect(onClick).not.toHaveBeenCalled();
  });

  it("applies the variant and size classes", () => {
    render(
      <Button variant="secondary" size="lg">
        Cancel
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Cancel" });
    // secondary => bordered white button; lg => the large padding scale.
    expect(button).toHaveClass("border", "bg-white", "px-6", "py-3");
  });
});
