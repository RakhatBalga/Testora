"use client";

import { useEffect, useRef, useState } from "react";
import { Pause, Play, RotateCcw, Volume2 } from "lucide-react";
import { mediaUrl, type ListeningMode } from "@/shared/api";

type Props = {
  src: string | null;
  mode: ListeningMode;
  sectionTitle: string;
  sectionStart: number;
  sectionEnd: number;
  initialPosition: number;
  onTimeChange: (position: number) => void;
  onEnded: () => void;
};

function clock(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  return `${Math.floor(safe / 60).toString().padStart(2, "0")}:${(safe % 60).toString().padStart(2, "0")}`;
}

export function ListeningAudioPlayer({
  src,
  mode,
  sectionTitle,
  sectionStart,
  sectionEnd,
  initialPosition,
  onTimeChange,
  onEnded,
}: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const initialized = useRef(false);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(initialPosition);
  const resolvedSrc = mediaUrl(src);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || initialized.current) return;
    const initialize = () => {
      audio.currentTime = mode === "exam" ? Math.max(0, initialPosition) : Math.max(sectionStart, initialPosition);
      setPosition(audio.currentTime);
      initialized.current = true;
    };
    if (audio.readyState >= 1) initialize();
    else audio.addEventListener("loadedmetadata", initialize, { once: true });
  }, [initialPosition, mode, sectionStart]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || mode !== "practice" || !initialized.current) return;
    audio.pause();
    audio.currentTime = sectionStart;
    setPosition(sectionStart);
    setPlaying(false);
  }, [mode, sectionStart]);

  const play = async () => {
    const audio = audioRef.current;
    if (!audio) return;
    await audio.play();
    setPlaying(true);
  };

  const pause = () => {
    if (mode === "exam") return;
    audioRef.current?.pause();
    setPlaying(false);
  };

  const restart = () => {
    const audio = audioRef.current;
    if (!audio || mode !== "practice") return;
    audio.currentTime = sectionStart;
    setPosition(sectionStart);
    onTimeChange(sectionStart);
  };

  const timeChanged = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (mode === "practice" && sectionEnd > sectionStart && audio.currentTime >= sectionEnd) {
      audio.pause();
      audio.currentTime = sectionEnd;
      setPlaying(false);
    }
    setPosition(audio.currentTime);
    onTimeChange(audio.currentTime);
  };

  const seek = (value: number) => {
    const audio = audioRef.current;
    if (!audio || mode !== "practice") return;
    audio.currentTime = value;
    setPosition(value);
    onTimeChange(value);
  };

  if (!resolvedSrc) {
    return <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">Audio is unavailable.</p>;
  }

  const sliderMin = mode === "practice" ? sectionStart : 0;
  const sliderMax = mode === "practice" ? sectionEnd : Math.max(sectionEnd, position + 1);
  const displayPosition = mode === "practice" ? position - sectionStart : position;
  const displayDuration = mode === "practice" ? sectionEnd - sectionStart : sliderMax;

  return (
    <div className="flex min-h-14 items-center gap-3 rounded-lg bg-slate-950 px-3 py-2 text-white">
      <audio
        ref={audioRef}
        src={resolvedSrc}
        preload="auto"
        onTimeUpdate={timeChanged}
        onEnded={onEnded}
        onPause={() => setPlaying(false)}
        onPlay={() => setPlaying(true)}
      />
      <button
        type="button"
        aria-label={playing ? "Pause audio" : "Play audio"}
        title={mode === "exam" && playing ? "Audio cannot be paused in Exam mode" : playing ? "Pause" : "Play"}
        disabled={mode === "exam" && playing}
        onClick={playing ? pause : play}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-white text-slate-950 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </button>
      {mode === "practice" && (
        <button type="button" aria-label="Restart section audio" title="Restart section" onClick={restart} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-white/10 hover:bg-white/20">
          <RotateCcw className="h-4 w-4" />
        </button>
      )}
      <Volume2 className="hidden h-4 w-4 shrink-0 text-slate-400 sm:block" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="truncate font-semibold">{sectionTitle}</span>
          <span className="shrink-0 tabular-nums text-slate-300">{clock(displayPosition)} / {clock(displayDuration)}</span>
        </div>
        <input
          aria-label="Audio position"
          type="range"
          min={sliderMin}
          max={sliderMax}
          step="0.1"
          value={Math.min(Math.max(position, sliderMin), sliderMax)}
          disabled={mode === "exam"}
          onChange={(event) => seek(Number(event.target.value))}
          className="mt-1 h-1.5 w-full accent-teal-400 disabled:cursor-default"
        />
      </div>
      <span className="hidden rounded-md bg-white/10 px-2 py-1 text-[11px] font-semibold uppercase sm:block">{mode}</span>
    </div>
  );
}
