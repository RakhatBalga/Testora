"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { BookmarkX, Loader2, Sparkles, Star } from "lucide-react";
import { api, type SavedWord } from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Button, Card, Skeleton } from "@/shared/ui";
import { DailyQuiz } from "./DailyQuiz";

export function VocabularyPage() {
  const { token, ready } = useRequireAuth();
  const [words, setWords] = useState<SavedWord[] | null>(null);
  const [trainingCount, setTrainingCount] = useState(0);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await api.listWords({ page: 1, page_size: 100 });
      setWords(data.items);
      setTrainingCount(data.training_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your words");
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    const t = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(t);
  }, [token, load]);

  if (!ready || !token) return null;

  const patch = (updated: SavedWord) =>
    setWords((ws) => ws?.map((w) => (w.id === updated.id ? updated : w)) ?? null);

  const enrich = async (w: SavedWord) => {
    setBusy(w.id);
    setError("");
    try {
      patch(await api.enrichWord(w.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fetch the meaning");
    } finally {
      setBusy(null);
    }
  };

  const toggleTrain = async (w: SavedWord) => {
    setBusy(w.id);
    setError("");
    try {
      const updated = await api.setWordTraining(w.id, !w.training);
      patch(updated);
      setTrainingCount((c) => c + (updated.training ? 1 : -1));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the word");
    } finally {
      setBusy(null);
    }
  };

  const remove = async (w: SavedWord) => {
    setBusy(w.id);
    setError("");
    try {
      await api.deleteWord(w.id);
      setWords((ws) => ws?.filter((x) => x.id !== w.id) ?? null);
      if (w.training) setTrainingCount((c) => Math.max(0, c - 1));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the word");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-[var(--brand)]">Save &amp; train words</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-950">Vocabulary</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Highlight any word while reading to save it here. Get its meaning,
          synonyms and native translation, then mark words to train and practise
          them with a daily quiz.
        </p>
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}

      <DailyQuiz />

      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-slate-950">
          Saved words{words ? ` (${words.length})` : ""}
        </h2>
        {trainingCount > 0 && (
          <span className="text-sm text-slate-500">{trainingCount} in training</span>
        )}
      </div>

      {!words ? (
        <div className="space-y-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      ) : words.length === 0 ? (
        <Card className="p-10 text-center">
          <Sparkles className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-3 font-semibold text-slate-800">No saved words yet</p>
          <p className="mt-1 text-sm text-slate-500">
            Open a{" "}
            <Link href="/tests/reading" className="font-semibold text-[var(--brand)]">
              Reading test
            </Link>{" "}
            and select any word in the passage to save it.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {words.map((w) => (
            <WordCard
              key={w.id}
              word={w}
              busy={busy === w.id}
              onEnrich={() => enrich(w)}
              onToggleTrain={() => toggleTrain(w)}
              onDelete={() => remove(w)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Chips({ items, tone }: { items?: string[]; tone: string }) {
  if (!items?.length) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-1.5">
      {items.map((s, i) => (
        <span key={i} className={`rounded-md px-2 py-0.5 text-xs font-medium ${tone}`}>
          {s}
        </span>
      ))}
    </div>
  );
}

function WordCard({
  word,
  busy,
  onEnrich,
  onToggleTrain,
  onDelete,
}: {
  word: SavedWord;
  busy: boolean;
  onEnrich: () => void;
  onToggleTrain: () => void;
  onDelete: () => void;
}) {
  const e = word.enrichment;
  const statusTone =
    word.status === "mastered"
      ? "bg-emerald-50 text-emerald-700"
      : word.status === "learning"
        ? "bg-blue-50 text-blue-700"
        : "bg-slate-100 text-slate-500";

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-lg font-bold text-slate-900">{word.word}</span>
            {e?.part_of_speech && (
              <span className="text-xs italic text-slate-400">{e.part_of_speech}</span>
            )}
            <span className={`rounded-md px-2 py-0.5 text-xs font-semibold capitalize ${statusTone}`}>
              {word.status}
            </span>
          </div>
          {word.context && (
            <p className="mt-1.5 line-clamp-2 border-l-2 border-slate-200 pl-3 text-sm italic text-slate-500">
              &ldquo;{word.context}&rdquo;
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={onToggleTrain}
            disabled={busy}
            aria-pressed={word.training}
            title={word.training ? "Remove from training" : "Train this word"}
            className={`flex h-9 w-9 items-center justify-center rounded-lg transition ${
              word.training
                ? "text-amber-500 hover:bg-amber-50"
                : "text-slate-300 hover:bg-slate-50 hover:text-slate-500"
            }`}
          >
            <Star className="h-5 w-5" fill={word.training ? "currentColor" : "none"} />
          </button>
          <button
            type="button"
            onClick={onDelete}
            disabled={busy}
            title="Delete word"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-300 transition hover:bg-red-50 hover:text-red-500"
          >
            <BookmarkX className="h-5 w-5" />
          </button>
        </div>
      </div>

      {e ? (
        <div className="mt-4 space-y-2.5 border-t border-slate-100 pt-4">
          {e.meaning && (
            <p className="text-sm text-slate-700">
              <span className="font-semibold text-slate-900">Meaning:</span> {e.meaning}
            </p>
          )}
          {e.translation && (
            <p className="text-sm text-slate-700">
              <span className="font-semibold text-slate-900">Translation:</span>{" "}
              {e.translation}
            </p>
          )}
          {e.synonyms?.length ? (
            <div>
              <span className="text-xs font-semibold text-slate-500">Synonyms</span>
              <Chips items={e.synonyms} tone="bg-slate-100 text-slate-600" />
            </div>
          ) : null}
          {e.alternatives?.length ? (
            <div>
              <span className="text-xs font-semibold text-slate-500">Better alternatives</span>
              <Chips items={e.alternatives} tone="bg-[var(--brand)]/[0.08] text-[var(--brand)]" />
            </div>
          ) : null}
          {e.example && (
            <p className="text-sm text-slate-500">
              <span className="font-semibold text-slate-600">Example:</span>{" "}
              <span className="italic">{e.example}</span>
            </p>
          )}
        </div>
      ) : (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <Button size="sm" variant="secondary" onClick={onEnrich} disabled={busy}>
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Looking up…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Get meaning &amp; synonyms
              </>
            )}
          </Button>
        </div>
      )}
    </Card>
  );
}
