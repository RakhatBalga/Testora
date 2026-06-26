import { type BandTrajectoryPoint } from "@/shared/api";

/**
 * Estimated overall band over time, with the target band drawn as a dashed
 * reference line. Pure SVG, no chart dependency.
 */
export function BandTrajectory({
  points,
  target,
}: {
  points: BandTrajectoryPoint[];
  target: number;
}) {
  const w = 720;
  const h = 240;
  const padX = 38;
  const padY = 30;
  const min = 4;
  const max = 9;

  const x = (i: number) => padX + (i * (w - padX * 2)) / Math.max(1, points.length - 1);
  const y = (band: number) => padY + (1 - (band - min) / (max - min)) * (h - padY * 2);

  const pts = points.map((p, i) => ({ ...p, cx: x(i), cy: y(p.band) }));
  const line = pts.map((p) => `${p.cx},${p.cy}`).join(" ");
  const area = `${padX},${h - padY} ${line} ${w - padX},${h - padY}`;
  const targetY = y(target);

  return (
    <div className="mt-5 w-full overflow-x-auto">
      <svg viewBox={`0 0 ${w} ${h}`} className="h-60 w-full min-w-[560px]">
        {/* gridlines + band labels */}
        {[9, 8, 7, 6, 5, 4].map((band) => {
          const gy = y(band);
          return (
            <g key={band}>
              <line x1={padX} y1={gy} x2={w - padX} y2={gy} stroke="var(--border)" strokeWidth={1} />
              <text x={8} y={gy + 4} fontSize={11} fill="var(--text-secondary)">
                {band}.0
              </text>
            </g>
          );
        })}

        {/* target reference line */}
        <line
          x1={padX}
          y1={targetY}
          x2={w - padX}
          y2={targetY}
          stroke="var(--brand)"
          strokeWidth={1.5}
          strokeDasharray="6 5"
          opacity={0.7}
        />
        <text
          x={w - padX}
          y={targetY - 7}
          fontSize={11}
          fontWeight={700}
          fill="var(--brand)"
          textAnchor="end"
        >
          Target {target.toFixed(1)}
        </text>

        {/* estimated band line + soft area */}
        <polygon points={area} fill="var(--brand)" opacity={0.08} />
        <polyline
          points={line}
          fill="none"
          stroke="var(--brand)"
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.cx} cy={p.cy} r={5} fill="white" stroke="var(--brand)" strokeWidth={3} />
            <text x={p.cx} y={h - 8} fontSize={11} fill="var(--text-secondary)" textAnchor="middle">
              {p.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
