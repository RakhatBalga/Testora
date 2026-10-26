"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth, useRequireAuth } from "@/shared/auth";
import { IELTS_TARGET_BAND } from "@/shared/config";
import { ErrorState } from "@/shared/ui";
import { AvatarCropper } from "@/features/avatar-crop";
import { useProfileEditor } from "@/features/profile-edit";
import { buildActivity, buildRecentItems, summarizeBands, useProfileData } from "@/entities/profile";
import {
  ActivityHeatmap,
  BandSnapshot,
  PracticeRecord,
  ProfileHeader,
  ProfileMetrics,
  RecentActivityList,
  StudySettings,
  TargetBandPicker,
} from "@/widgets/profile";

export default function ProfilePage() {
  const { token, ready } = useRequireAuth();
  const { username, logout } = useAuth();
  const router = useRouter();

  const { profile, setProfile, attempts, writing, speaking, loading, error, reload } = useProfileData(token);
  const targetBand = profile?.target_band ?? IELTS_TARGET_BAND;
  const editor = useProfileEditor(profile, setProfile, targetBand);

  const sources = useMemo(() => ({ attempts, writing, speaking }), [attempts, writing, speaking]);
  const { avgBand, bestBand, skillBands } = useMemo(() => summarizeBands(sources), [sources]);
  const recentItems = useMemo(() => buildRecentItems(sources), [sources]);
  const activity = useMemo(() => buildActivity(sources), [sources]);

  const readingCount = attempts.filter((a) => a.test_type === "reading").length;
  const listeningCount = attempts.filter((a) => a.test_type === "listening").length;
  const totalSessions = attempts.length + writing.length + speaking.length;

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (!ready || !token) return null;

  return (
    <div className="space-y-6">
      {editor.cropFile && (
        <AvatarCropper
          file={editor.cropFile}
          saving={editor.savingAvatar}
          onCancel={() => editor.setCropFile(null)}
          onSave={editor.handleCropSave}
        />
      )}

      <ProfileHeader
        profile={profile}
        username={username}
        loading={loading}
        totalSessions={totalSessions}
        targetBand={targetBand}
        savingAvatar={editor.savingAvatar}
        avatarInputRef={editor.avatarInputRef}
        onAvatarSelect={editor.handleAvatarSelect}
        onAvatarRemove={editor.handleAvatarRemove}
        onLogout={handleLogout}
      />

      {error && <ErrorState message={error} onRetry={reload} />}
      {editor.actionError && <ErrorState message={editor.actionError} />}

      <BandSnapshot loading={loading} avgBand={avgBand} skillBands={skillBands} targetBand={targetBand} />
      <ActivityHeatmap loading={loading} activity={activity} />
      <TargetBandPicker
        loading={loading}
        targetBand={targetBand}
        savingTarget={editor.savingTarget}
        onChange={editor.handleTargetChange}
      />
      {profile && (
        <StudySettings
          profile={profile}
          setProfile={setProfile}
          resettingPlan={editor.resettingPlan}
          savingSettings={editor.savingSettings}
          onReset={editor.handlePlanReset}
          onSave={editor.handleSettingsSave}
        />
      )}
      <ProfileMetrics
        loading={loading}
        totalSessions={totalSessions}
        avgBand={avgBand}
        bestBand={bestBand}
        aiReviews={writing.length + speaking.length}
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <PracticeRecord
          loading={loading}
          readingCount={readingCount}
          listeningCount={listeningCount}
          writingCount={writing.length}
          speakingCount={speaking.length}
        />
        <RecentActivityList loading={loading} items={recentItems} />
      </div>
    </div>
  );
}
