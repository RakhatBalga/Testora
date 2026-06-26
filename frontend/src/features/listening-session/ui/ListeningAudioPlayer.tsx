import { Volume2 } from "lucide-react";

type Props = {
  src: string | null;
  sectionTitle: string;
};

/**
 * Compact, single-row audio bar (~64px). Still prominent — brand-coloured and
 * first in the reading order — but no longer a tall hero. Icon + section label
 * sit inline with the native control, which flexes to fill the remaining width.
 * `key` forces a reload when the section (src) changes.
 */
export function ListeningAudioPlayer({ src, sectionTitle }: Props) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-[var(--brand)] px-3 py-2 text-white shadow-md shadow-[var(--brand)]/20">
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-white/15">
        <Volume2 className="h-4.5 w-4.5" />
      </span>
      <p className="hidden w-52 flex-shrink-0 truncate text-sm font-semibold leading-tight lg:block">
        {sectionTitle}
      </p>
      {src ? (
        <audio key={src} controls autoPlay className="h-9 min-w-0 flex-1" preload="auto">
          <source src={src} />
          Your browser does not support audio playback.
        </audio>
      ) : (
        <p className="flex-1 text-sm text-white/80">No audio for this section.</p>
      )}
    </div>
  );
}
