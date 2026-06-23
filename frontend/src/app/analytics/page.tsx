"use client";

import { Target, TrendingUp, Crosshair, Clock, CheckCircle2 } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import {
  SKILLS,
  skillMeta,
  toneClasses,
  learner,
  bandHistory,
  skillSeries,
} from "@/lib/dashboard";
import { PageHeader, StatTile, ProgressBar, skillIcons } from "@/components/dashboard/widgets";

export default function AnalyticsPage() {
  const { token, ready } = useRequireAuth();
  if (!ready || !token) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        subtitle="Track your band trajectory and see exactly where to focus next."
      />

      {/* metric cards */}
      <div className="grid animate-fade-up gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatTile label="Current Band" value={learner.currentBand.toFixed(1)} icon={<TrendingUp className="h-5 w-5" />} />
        <StatTile label="Target Band" value={learner.targetBand.toFixed(1)} icon={<Target className="h-5 w-5" />} />
        <StatTile label="Accuracy" value={`${Math.round(learner.accuracy * 100)}%`} icon={<Crosshair className="h-5 w-5" />} accent="text-emerald-500" />
        <StatTile label="Study Time" value={`${learner.studyTimeHours}h`} icon={<Clock className="h-5 w-5" />} accent="text-sky-500" />
        <StatTile label="Completion" value={`${Math.round(learner.completionRate * 100)}%`} icon={<CheckCircle2 className="h-5 w-5" />} accent="text-amber-500" />
      </div>

      {/* band history line chart */}
      <section className="animate-fade-up rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40 [animation-delay:80ms] sm:p-7">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Band Score history</h2>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
            <TrendingUp className="h-3.5 w-3.5" />
            +{(bandHistory[bandHistory.length - 1].band - bandHistory[0].band).toFixed(1)} over 6 weeks
          </span>
        </div>
        <BandLineChart />
      </section>

      {/* per-skill progress */}
      <section className="grid animate-fade-up gap-5 [animation-delay:120ms] sm:grid-cols-2">
        {SKILLS.map((s) => {
          const m = skillMeta[s];
          const t = toneClasses[m.tone];
          const Icon = skillIcons[s];
          const series = skillSeries[s];
          return (
            <div
              key={s}
              className="rounded-3xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${t.soft}`}>
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="font-semibold text-[var(--text-primary)]">{m.label} progress</h3>
                </div>
                <span className="text-sm font-bold text-[var(--text-primary)]">
                  {Math.round(m.progress * 100)}%
                </span>
              </div>

              {/* weekly bars */}
              <div className="mt-5 flex h-24 items-end gap-2">
                {series.map((v, i) => (
                  <div key={i} className="flex flex-1 flex-col items-center gap-1.5">
                    <div className="flex w-full flex-1 items-end">
                      <div
                        className={`w-full rounded-t-md ${t.bar} transition-[height] duration-500`}
                        style={{ height: `${Math.max(8, v * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[var(--text-secondary)]">W{i + 1}</span>
                  </div>
                ))}
              </div>

              <div className="mt-4">
                <ProgressBar value={m.progress} barClass={t.bar} />
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}

function BandLineChart() {
  const w = 720;
  const h = 220;
  const padX = 36;
  const padY = 28;
  const min = 4;
  const max = 9;
  const pts = bandHistory.map((d, i) => {
    const x = padX + (i * (w - padX * 2)) / (bandHistory.length - 1);
    const y = padY + (1 - (d.band - min) / (max - min)) * (h - padY * 2);
    return { x, y, ...d };
  });
  const line = pts.map((p) => `${p.x},${p.y}`).join(" ");
  const area = `${padX},${h - padY} ${line} ${w - padX},${h - padY}`;

  return (
    <div className="mt-5 w-full overflow-x-auto">
      <svg viewBox={`0 0 ${w} ${h}`} className="h-56 w-full min-w-[560px]">
        {[9, 8, 7, 6, 5, 4].map((band) => {
          const y = padY + (1 - (band - min) / (max - min)) * (h - padY * 2);
          return (
            <g key={band}>
              <line x1={padX} y1={y} x2={w - padX} y2={y} stroke="var(--border)" strokeWidth={1} />
              <text x={8} y={y + 4} fontSize={11} fill="var(--text-secondary)">
                {band}.0
              </text>
            </g>
          );
        })}

        <polygon points={area} fill="var(--brand)" opacity={0.08} />
        <polyline points={line} fill="none" stroke="var(--brand)" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />

        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={5} fill="white" stroke="var(--brand)" strokeWidth={3} />
            <text x={p.x} y={h - 8} fontSize={11} fill="var(--text-secondary)" textAnchor="middle">
              {p.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
