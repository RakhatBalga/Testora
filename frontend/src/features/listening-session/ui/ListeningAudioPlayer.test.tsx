import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ListeningAudioPlayer } from "./ListeningAudioPlayer";

it.each([0, 1])("restores the saved position when metadata is %s (loading/ready)", (readyState) => {
  const ready = vi.spyOn(HTMLMediaElement.prototype, "readyState", "get").mockReturnValue(readyState);
  const { container } = render(<ListeningAudioPlayer src="/audio.m4a" mode="practice" sectionTitle="Section 2" sectionStart={100} sectionEnd={200} initialPosition={145} onTimeChange={vi.fn()} onEnded={vi.fn()} />);
  const audio = container.querySelector("audio")!;
  if (!readyState) fireEvent.loadedMetadata(audio);
  expect(audio.currentTime).toBe(145);
  expect(screen.getByRole("slider", { name: "Audio position" })).toHaveValue("145");
  ready.mockRestore();
});
