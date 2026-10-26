/** Turn a getUserMedia/MediaRecorder failure into guidance a student can act on. */
export function micErrorMessage(error: unknown): string {
  const name = error instanceof DOMException || error instanceof Error ? error.name : "";
  switch (name) {
    case "NotAllowedError":
    case "SecurityError":
    case "PermissionDeniedError":
      return "Microphone access is blocked. Allow the microphone for this site in your browser settings (on iPhone: Settings > Safari > Microphone), then try again.";
    case "NotFoundError":
    case "DevicesNotFoundError":
      return "No microphone was found. Connect one and try again.";
    case "NotReadableError":
    case "TrackStartError":
      return "The microphone is in use by another app. Close it and try again.";
    case "OverconstrainedError":
      return "This microphone is not supported. Try a different one.";
    default:
      return "Could not start recording. Check your microphone and try again.";
  }
}
