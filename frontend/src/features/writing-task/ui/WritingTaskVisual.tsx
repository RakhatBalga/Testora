"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowRight, Map } from "lucide-react";
import type { WritingVisualData } from "@/shared/api";

const COLORS = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"];

function chartRows(data: WritingVisualData) {
  return (data.categories ?? []).map((category, index) => ({
    category,
    ...(data.series ?? []).reduce<Record<string, number>>((row, series) => {
      row[series.name] = series.values[index] ?? 0;
      return row;
    }, {}),
  }));
}

export function WritingTaskVisual({ data }: { data: WritingVisualData }) {
  return (
    <figure className="mt-5 border-t border-slate-200 pt-5" aria-label={data.title ?? "Writing task visual"}>
      {data.title && (
        <figcaption className="mb-4 text-center text-sm font-semibold text-slate-800">
          {data.title}
          {data.unit ? <span className="ml-1 font-normal text-slate-500">({data.unit})</span> : null}
        </figcaption>
      )}
      {data.kind === "line" && <SeriesChart data={data} kind="line" />}
      {data.kind === "bar" && <SeriesChart data={data} kind="bar" />}
      {data.kind === "table" && <DataTable data={data} />}
      {data.kind === "pie" && <PieComparison data={data} />}
      {data.kind === "process" && <ProcessDiagram steps={data.steps ?? []} />}
      {data.kind === "map" && <MapComparison before={data.before ?? []} after={data.after ?? []} />}
    </figure>
  );
}

function SeriesChart({ data, kind }: { data: WritingVisualData; kind: "line" | "bar" }) {
  const rows = chartRows(data);
  const series = data.series ?? [];
  return (
    <div className="h-80 w-full" role="img" aria-label={`${kind} chart: ${data.title ?? "Task 1 data"}`}>
      <ResponsiveContainer width="100%" height="100%">
        {kind === "line" ? (
          <LineChart data={rows} margin={{ top: 10, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="category" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {series.map((item, index) => (
              <Line key={item.name} type="monotone" dataKey={item.name} stroke={COLORS[index % COLORS.length]} strokeWidth={2.5} dot={{ r: 3 }} />
            ))}
          </LineChart>
        ) : (
          <BarChart data={rows} margin={{ top: 10, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="category" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {series.map((item, index) => (
              <Bar key={item.name} dataKey={item.name} fill={COLORS[index % COLORS.length]} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

function DataTable({ data }: { data: WritingVisualData }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] border-collapse text-sm">
        <thead>
          <tr className="bg-slate-100 text-left text-slate-700">
            {(data.columns ?? []).map((column) => (
              <th key={column} className="border border-slate-200 px-4 py-3 font-semibold">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(data.rows ?? []).map((row, rowIndex) => (
            <tr key={rowIndex} className="even:bg-slate-50">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="border border-slate-200 px-4 py-3 text-slate-700">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PieComparison({ data }: { data: WritingVisualData }) {
  return (
    <div className="grid gap-6 sm:grid-cols-2">
      {(data.charts ?? []).map((chart) => (
        <div key={chart.title}>
          <p className="text-center text-sm font-semibold text-slate-700">{chart.title}</p>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={chart.values} dataKey="value" nameKey="name" cx="50%" cy="47%" outerRadius={78} label={({ value }) => `${value}%`}>
                  {chart.values.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(value) => `${value}%`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
    </div>
  );
}

function ProcessDiagram({ steps }: { steps: string[] }) {
  return (
    <ol className="mx-auto grid max-w-2xl gap-2">
      {steps.map((step, index) => (
        <li key={step}>
          <div className="flex min-h-24 items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">{index + 1}</span>
            <span className="text-sm leading-5 text-slate-700">{step}</span>
          </div>
          {index < steps.length - 1 && <ArrowRight className="mx-auto mt-2 h-5 w-5 rotate-90 text-slate-400" aria-hidden="true" />}
        </li>
      ))}
    </ol>
  );
}

function MapComparison({ before, after }: { before: string[]; after: string[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <MapPanel title="Present day" items={before} tone="bg-slate-50" />
      <MapPanel title="Planned for 2030" items={after} tone="bg-emerald-50" />
    </div>
  );
}

function MapPanel({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <div className={`min-h-72 rounded-lg border border-slate-200 p-5 ${tone}`}>
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
        <Map className="h-4 w-4 text-slate-600" />
        <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      </div>
      <ul className="mt-4 grid gap-3">
        {items.map((item) => <li key={item} className="rounded-md border border-white bg-white/90 px-3 py-2 text-sm leading-5 text-slate-700 shadow-sm">{item}</li>)}
      </ul>
    </div>
  );
}
