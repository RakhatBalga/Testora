"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/shared/ui";

// On-screen diameter of the circular crop window and the exported image size.
const VIEWPORT = 288;
const OUTPUT = 512;
const MAX_ZOOM = 3;

type Props = {
  file: File;
  saving?: boolean;
  onCancel: () => void;
  onSave: (blob: Blob) => void;
};

type Natural = { w: number; h: number };

/**
 * Circular avatar cropper. The user drags to reposition and uses the slider (or
 * wheel) to zoom; on save we render the visible circle's bounding square to a
 * canvas and hand back a JPEG blob. The image always "covers" the viewport, and
 * panning is clamped so no empty gaps can appear inside the circle.
 */
export function AvatarCropper({ file, saving = false, onCancel, onSave }: Props) {
  const imgRef = useRef<HTMLImageElement>(null);
  const url = useMemo(() => URL.createObjectURL(file), [file]);
  const [natural, setNatural] = useState<Natural | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ px: number; py: number } | null>(null);

  useEffect(() => () => URL.revokeObjectURL(url), [url]);

  const coverScale = natural
    ? Math.max(VIEWPORT / natural.w, VIEWPORT / natural.h)
    : 1;
  const scale = coverScale * zoom;
  const dw = natural ? natural.w * scale : VIEWPORT;
  const dh = natural ? natural.h * scale : VIEWPORT;

  const clamp = useCallback(
    (next: { x: number; y: number }, displayW: number, displayH: number) => {
      const maxX = Math.max(0, (displayW - VIEWPORT) / 2);
      const maxY = Math.max(0, (displayH - VIEWPORT) / 2);
      return {
        x: Math.min(maxX, Math.max(-maxX, next.x)),
        y: Math.min(maxY, Math.max(-maxY, next.y)),
      };
    },
    [],
  );

  const applyZoom = (nextZoom: number) => {
    const z = Math.min(MAX_ZOOM, Math.max(1, nextZoom));
    setZoom(z);
    if (natural) {
      const s = coverScale * z;
      setPan((p) => clamp(p, natural.w * s, natural.h * s));
    }
  };

  const onPointerDown = (e: React.PointerEvent) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { px: e.clientX, py: e.clientY };
    setDragging(true);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const nx = pan.x + (e.clientX - drag.current.px);
    const ny = pan.y + (e.clientY - drag.current.py);
    drag.current = { px: e.clientX, py: e.clientY };
    setPan(clamp({ x: nx, y: ny }, dw, dh));
  };
  const onPointerUp = (e: React.PointerEvent) => {
    drag.current = null;
    setDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  const handleSave = () => {
    const img = imgRef.current;
    if (!img || !natural) return;
    const s = coverScale * zoom;
    const srcSize = VIEWPORT / s; // side of the source square, in image pixels
    const centerX = natural.w / 2 - pan.x / s;
    const centerY = natural.h / 2 - pan.y / s;
    const canvas = document.createElement("canvas");
    canvas.width = OUTPUT;
    canvas.height = OUTPUT;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(
      img,
      centerX - srcSize / 2,
      centerY - srcSize / 2,
      srcSize,
      srcSize,
      0,
      0,
      OUTPUT,
      OUTPUT,
    );
    canvas.toBlob((blob) => blob && onSave(blob), "image/jpeg", 0.9);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">Position your photo</h2>
        <p className="mt-1 text-sm text-slate-500">Drag to move, use the slider to zoom.</p>

        <div className="mt-5 flex justify-center">
          <div
            className={`relative touch-none overflow-hidden rounded-full bg-slate-100 ${
              dragging ? "cursor-grabbing" : "cursor-grab"
            }`}
            style={{ width: VIEWPORT, height: VIEWPORT }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            onWheel={(e) => applyZoom(zoom - e.deltaY * 0.002)}
          >
            {url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                ref={imgRef}
                src={url}
                alt=""
                draggable={false}
                onLoad={(e) =>
                  setNatural({
                    w: e.currentTarget.naturalWidth,
                    h: e.currentTarget.naturalHeight,
                  })
                }
                style={{
                  position: "absolute",
                  width: dw,
                  height: dh,
                  left: (VIEWPORT - dw) / 2 + pan.x,
                  top: (VIEWPORT - dh) / 2 + pan.y,
                  maxWidth: "none",
                  opacity: natural ? 1 : 0,
                  userSelect: "none",
                }}
              />
            )}
            <div className="pointer-events-none absolute inset-0 rounded-full ring-1 ring-inset ring-slate-900/10" />
          </div>
        </div>

        <input
          type="range"
          min={1}
          max={MAX_ZOOM}
          step={0.01}
          value={zoom}
          onChange={(e) => applyZoom(Number(e.target.value))}
          aria-label="Zoom"
          className="mt-5 w-full accent-[var(--brand)]"
        />

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || !natural}>
            {saving ? "Saving..." : "Save photo"}
          </Button>
        </div>
      </div>
    </div>
  );
}
