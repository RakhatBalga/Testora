"use client";

import { useEffect, useState } from "react";
import { Play, Square, Volume2 } from "lucide-react";
import { mediaUrl } from "@/shared/api";

type Props = {
  src: string | null;
  transcript?: string | null;
  sectionTitle: string;
};

/**
 * Compact, single-row audio bar (~64px). Still prominent — brand-coloured and
 * first in the reading order — but no longer a tall hero. Icon + section label
 * sit inline with the native control, which flexes to fill the remaining width.
 * `key` forces a reload when the section (src) changes.
 */
export function ListeningAudioPlayer({ src, transcript, sectionTitle }: Props) {
  const [speaking, setSpeaking] = useState(false);
  const resolvedSrc = mediaUrl(src);
  const canSpeak = !resolvedSrc && !!transcript && typeof window !== "undefined";

  useEffect(() => {
    return () => window.speechSynthesis?.cancel();
  }, []);

  const toggleSpeech = () => {
    if (!transcript || typeof window === "undefined") return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(transcript);
    utterance.rate = 0.92;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  };

  return (
    <div className="flex items-center gap-3 rounded-xl bg-[var(--brand)] px-3 py-2 text-white shadow-md shadow-[var(--brand)]/20">
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-white/15">
        <Volume2 className="h-4.5 w-4.5" />
      </span>
      <p className="hidden w-52 flex-shrink-0 truncate text-sm font-semibold leading-tight lg:block">
        {sectionTitle}
      </p>
      {resolvedSrc ? (
        <audio key={resolvedSrc} controls autoPlay className="h-9 min-w-0 flex-1" preload="auto">
          <source src={resolvedSrc} />
          Your browser does not support audio playback.
        </audio>
      ) : canSpeak ? (
        <button
          type="button"
          onClick={toggleSpeech}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-white/15 px-3 py-2 text-sm font-semibold transition hover:bg-white/20"
        >
          {speaking ? <Square className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          {speaking ? "Stop transcript audio" : "Play transcript audio"}
        </button>
      ) : (
        <p className="flex-1 text-sm text-white/80">No audio for this section.</p>
      )}
    </div>
  );
}
