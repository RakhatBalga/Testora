"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { Clock3, Headphones, ListChecks, Pause, Play, ShieldCheck } from "lucide-react";
import {
  api,
  type AnswerValue,
  type ListeningMode,
  type ListeningProgress,
  type ListeningTest,
  type TestDetail,
} from "@/shared/api";
import { useRequireAuth } from "@/shared/auth";
import { Button, Card, Skeleton } from "@/shared/ui";
import {
  buildGroups,
  flattenQuestions,
  isAnswered,
  type AnswerMap,
} from "@/features/reading-session";
import { useReadingTimer } from "@/features/reading-session";
import {
  ListeningAudioPlayer,
  ListeningQuestions,
  ListeningSectionNav,
  SubmitConfirm,
} from "@/features/listening-session";

function asGroups(test: ListeningTest) {
  const compatible: TestDetail = {
    id: test.id,
    title: test.title,
    test_type: "listening",
    description: test.description,
    duration_minutes: test.duration_minutes,
    difficulty: test.difficulty,
    question_count: test.question_count,
    sections: test.sections.map((section) => ({
      id: section.id,
      order: section.order,
      title: section.title,
      instructions: section.instructions,
      passage: null,
      audio_url: section.audio_url,
      questions: section.questions.map((question) => ({ ...question, evidence: null })),
    })),
  };
  return buildGroups(compatible);
}

function ModeChooser({ test, onStart, busy }: { test: ListeningTest; onStart: (mode: ListeningMode) => void; busy: boolean }) {
  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-16 pt-4">
      <div>
        <p className="text-sm font-semibold uppercase text-teal-700">Listening benchmark</p>
        <h1 className="mt-1 text-3xl font-extrabold text-slate-950">{test.title}</h1>
        <p className="mt-2 text-sm text-slate-500">{test.authorship}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-6">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-950 text-white"><ShieldCheck className="h-5 w-5" /></div>
          <h2 className="mt-4 text-xl font-bold text-slate-950">Exam mode</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">One continuous recording. Audio cannot be paused, replayed, or moved backwards.</p>
          <Button className="mt-6 w-full" disabled={busy} onClick={() => onStart("exam")}><Headphones className="h-4 w-4" /> Start exam</Button>
        </Card>
        <Card className="p-6">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-teal-50 text-teal-700"><Play className="h-5 w-5" /></div>
          <h2 className="mt-4 text-xl font-bold text-slate-950">Practice mode</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Pause, replay, and move within the current section. Answers stay hidden until submission.</p>
          <Button variant="secondary" className="mt-6 w-full" disabled={busy} onClick={() => onStart("practice")}><Play className="h-4 w-4" /> Start practice</Button>
        </Card>
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-500">
        <span>{test.question_count} questions</span><span>4 sections</span><span>{test.duration_minutes} min recording</span><span className="capitalize">{test.calibration_status} calibration</span>
      </div>
    </div>
  );
}

function clock(seconds: number | null): string {
  if (seconds === null) return "--:--";
  return `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;
}

function ActiveSession({ test, mode, initial }: { test: ListeningTest; mode: ListeningMode; initial: ListeningProgress | null }) {
  const router = useRouter();
  const groups = useMemo(() => asGroups(test), [test]);
  const flat = useMemo(() => flattenQuestions(groups), [groups]);
  const initialAnswers = useMemo(() => Object.fromEntries(Object.entries(initial?.answers ?? {}).map(([key, value]) => [Number(key), value])) as AnswerMap, [initial]);
  const [answers, setAnswers] = useState<AnswerMap>(initialAnswers);
  const [activeSection, setActiveSection] = useState(initial?.current_section ?? 0);
  const [activeNumber, setActiveNumber] = useState(groups[initial?.current_section ?? 0]?.start ?? 1);
  const [audioPosition, setAudioPosition] = useState(initial?.audio_position ?? 0);
  const [maxAudioPosition, setMaxAudioPosition] = useState(initial?.max_audio_position ?? 0);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const submitted = useRef(false);
  const stateRef = useRef({ answers, activeSection, audioPosition, maxAudioPosition });
  const timerRef = useRef<number | null>(null);
  const sessionKey = `listening-${test.id}-${test.content_version}-${mode}`;
  const section = test.sections[activeSection];
  const answeredCount = flat.filter((question) => isAnswered(answers[question.id])).length;

  const handleSubmit = useCallback(async () => {
    if (submitted.current) return;
    submitted.current = true;
    setSubmitting(true);
    setError("");
    try {
      let submissionKey = localStorage.getItem(`${sessionKey}-submission-key`);
      if (!submissionKey) {
        submissionKey = crypto.randomUUID();
        localStorage.setItem(`${sessionKey}-submission-key`, submissionKey);
      }
      const result = await api.submitListening(test.id, {
        content_version: test.content_version,
        mode,
        submission_key: submissionKey,
        answers: flat.map((question) => ({ question_id: question.id, answer: answers[question.id] ?? null })),
        duration_seconds: Math.max(0, test.duration_minutes * 60 - (timerRef.current ?? 0)),
      });
      localStorage.removeItem(`${sessionKey}-timer`);
      localStorage.removeItem(`${sessionKey}-submission-key`);
      localStorage.removeItem(`listening-${test.id}-mode`);
      router.push(`/listening/result/${result.attempt_id}`);
    } catch (caught) {
      submitted.current = false;
      setError(caught instanceof Error ? caught.message : "Could not submit the test");
    } finally {
      setSubmitting(false);
    }
  }, [answers, flat, mode, router, sessionKey, test]);

  const { remaining, paused, pause, resume } = useReadingTimer(sessionKey, test.duration_minutes * 60, handleSubmit);

  useEffect(() => { timerRef.current = remaining; }, [remaining]);
  useEffect(() => { stateRef.current = { answers, activeSection, audioPosition, maxAudioPosition }; }, [answers, activeSection, audioPosition, maxAudioPosition]);
  const persistProgress = useCallback(() => {
    const current = stateRef.current;
    return api.saveListeningProgress(test.id, {
      content_version: test.content_version,
      mode,
      answers: Object.fromEntries(Object.entries(current.answers).map(([key, value]) => [String(key), value])),
      current_section: current.activeSection,
      audio_position: current.audioPosition,
      max_audio_position: current.maxAudioPosition,
    });
  }, [mode, test.content_version, test.id]);
  useEffect(() => {
    const interval = window.setInterval(() => {
      void persistProgress().catch(() => undefined);
    }, 10000);
    return () => window.clearInterval(interval);
  }, [persistProgress]);
  useEffect(() => {
    const timeout = window.setTimeout(() => void persistProgress().catch(() => undefined), 500);
    return () => window.clearTimeout(timeout);
  }, [answers, activeSection, persistProgress]);

  const answer = (questionId: number, value: AnswerValue) => {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  };

  const audioTime = (position: number) => {
    setAudioPosition(position);
    setMaxAudioPosition((current) => Math.max(current, position));
    if (mode === "exam") {
      const next = test.sections.findLastIndex((item) => position >= item.audio_start);
      if (next >= 0 && next !== activeSection) {
        setActiveSection(next);
        setActiveNumber(groups[next].start);
      }
    }
  };

  const selectSection = (index: number) => {
    if (mode === "exam" || index < 0 || index >= groups.length) return;
    setActiveSection(index);
    setActiveNumber(groups[index].start);
  };

  return (
    <div className="pb-14">
      <div className="sticky top-[57px] z-30 -mx-5 space-y-2 border-b border-slate-200 bg-white/95 px-5 py-2 backdrop-blur sm:-mx-8 sm:px-8">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0"><h1 className="truncate text-sm font-bold text-slate-950">{test.title}</h1><p className="text-xs text-slate-500">Section {activeSection + 1} of 4 · {answeredCount}/{flat.length} answered</p></div>
          <div className="flex shrink-0 items-center gap-2">
            <div className={`flex h-9 items-center gap-1.5 rounded-lg px-2.5 font-mono text-sm font-semibold ${remaining !== null && remaining < 60 ? "bg-red-50 text-red-700" : "bg-slate-100 text-slate-700"}`}><Clock3 className="h-4 w-4" />{clock(remaining)}</div>
            {mode === "practice" && <button type="button" aria-label={paused ? "Resume timer" : "Pause timer"} onClick={paused ? resume : pause} className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200">{paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}</button>}
            <Button size="sm" onClick={() => setConfirmOpen(true)}><ListChecks className="h-4 w-4" /> Submit</Button>
          </div>
        </div>
        <ListeningAudioPlayer
          src={section.audio_url}
          mode={mode}
          sectionTitle={mode === "exam" && audioPosition < test.sections[0].audio_start ? "Test introduction" : section.title}
          sectionStart={section.audio_start}
          sectionEnd={section.audio_end}
          initialPosition={audioPosition}
          onTimeChange={audioTime}
          onEnded={() => setConfirmOpen(true)}
        />
        <div className={mode === "exam" ? "pointer-events-none opacity-70" : ""}>
          <ListeningSectionNav sections={groups} active={activeSection} answers={answers} onSelect={selectSection} />
        </div>
      </div>
      {error && <p className="mx-auto mt-4 max-w-3xl rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <main className="mx-auto mt-5 max-w-3xl space-y-5">
        {section.map_asset && <Image src={section.map_asset} alt="Map for Section 2 questions" width={800} height={520} priority className="h-auto w-full rounded-lg border border-slate-200 bg-white" />}
        <ListeningQuestions section={groups[activeSection]} answers={answers} activeNumber={activeNumber} onAnswer={answer} onFocusQuestion={setActiveNumber} />
      </main>
      <SubmitConfirm open={confirmOpen} answered={answeredCount} total={flat.length} submitting={submitting} onConfirm={handleSubmit} onCancel={() => setConfirmOpen(false)} />
    </div>
  );
}

export default function ListeningPage() {
  const { token, ready } = useRequireAuth();
  const params = useParams();
  const testId = Number(params?.id);
  const [test, setTest] = useState<ListeningTest | null>(null);
  const [mode, setMode] = useState<ListeningMode | null>(null);
  const [progress, setProgress] = useState<ListeningProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api.getListeningTest(testId).then(setTest).catch((caught) => setError(caught instanceof Error ? caught.message : "Could not load listening test")).finally(() => setLoading(false));
  }, [testId, token]);

  const start = async (selected: ListeningMode) => {
    if (!test) return;
    setStarting(true);
    try {
      const saved = await api.getListeningProgress(test.id, test.content_version, selected);
      setProgress(saved?.status === "in_progress" ? saved : null);
      setMode(selected);
      localStorage.setItem(`listening-${test.id}-mode`, selected);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start the session");
    } finally {
      setStarting(false);
    }
  };

  if (!ready || !token) return null;
  if (loading) return <div className="space-y-4"><Skeleton className="h-24 w-full" /><Skeleton className="h-72 w-full" /></div>;
  if (error) return <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>;
  if (!test) return <Card className="p-8 text-center text-slate-500">Listening test is unavailable.</Card>;
  if (!mode) return <ModeChooser test={test} onStart={start} busy={starting} />;
  return <ActiveSession test={test} mode={mode} initial={progress} />;
}
