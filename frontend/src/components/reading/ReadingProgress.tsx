type Props = {
  answered: number;
  total: number;
};

export function ReadingProgress({ answered, total }: Props) {
  const remaining = total - answered;
  const pct = total === 0 ? 0 : Math.round((answered / total) * 100);

  return (
    <div className="w-full">
      <div className="mb-1.5 flex items-center justify-between text-xs font-medium">
        <span className="text-slate-600">
          Answered <strong className="text-slate-900">{answered}</strong> / {total}
        </span>
        <span className="text-slate-400">
          {remaining} left · {pct}%
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-[var(--brand)] transition-[width] duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
