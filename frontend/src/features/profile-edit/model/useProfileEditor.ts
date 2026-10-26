"use client";

import { useRef, useState, type ChangeEvent, type Dispatch, type SetStateAction } from "react";
import { api, type UserProfile } from "@/shared/api";
import { useAuth } from "@/shared/auth";

/** Profile mutations: avatar upload/removal, target band, study settings, plan reset. */
export function useProfileEditor(
  profile: UserProfile | null,
  setProfile: Dispatch<SetStateAction<UserProfile | null>>,
  targetBand: number,
) {
  const { setAvatar } = useAuth();
  const [savingTarget, setSavingTarget] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [savingAvatar, setSavingAvatar] = useState(false);
  const [resettingPlan, setResettingPlan] = useState(false);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [actionError, setActionError] = useState("");
  const avatarInputRef = useRef<HTMLInputElement>(null);

  const handleAvatarSelect = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-selecting the same file later
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setActionError("Avatar must be an image file.");
      return;
    }
    setActionError("");
    setCropFile(file); // open the cropper; upload happens on save
  };

  const handleCropSave = async (blob: Blob) => {
    if (savingAvatar) return;
    setSavingAvatar(true);
    try {
      const file = new File([blob], "avatar.jpg", { type: "image/jpeg" });
      const updated = await api.uploadAvatar(file);
      setProfile((prev) => (prev ? { ...prev, avatar: updated.avatar } : updated));
      setAvatar(updated.avatar);
      setCropFile(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Avatar failed to upload.");
    } finally {
      setSavingAvatar(false);
    }
  };

  const handleAvatarRemove = async () => {
    if (!profile?.avatar || savingAvatar) return;
    setActionError("");
    setSavingAvatar(true);
    try {
      const updated = await api.deleteAvatar();
      setProfile((prev) => (prev ? { ...prev, avatar: updated.avatar } : updated));
      setAvatar(updated.avatar);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Avatar failed to remove.");
    } finally {
      setSavingAvatar(false);
    }
  };

  const handleTargetChange = async (band: number) => {
    if (savingTarget || band === targetBand) return;
    if (profile?.current_level !== null && profile?.current_level !== undefined && band < profile.current_level) {
      setActionError("Target band cannot be below your current level.");
      return;
    }
    const previous = profile;
    setActionError("");
    setSavingTarget(true);
    if (previous) setProfile({ ...previous, target_band: band });
    try {
      const updated = await api.updateProfile(band);
      setProfile(updated);
    } catch (err) {
      if (previous) setProfile(previous);
      setActionError(err instanceof Error ? err.message : "Target band failed to save.");
    } finally {
      setSavingTarget(false);
    }
  };

  const handleSettingsSave = async () => {
    if (!profile || savingSettings) return;
    setSavingSettings(true);
    setActionError("");
    try {
      setProfile(await api.updateProfile({
        current_level: profile.current_level,
        exam_date: profile.exam_date,
        weekly_study_days: profile.weekly_study_days,
        daily_study_minutes: profile.daily_study_minutes,
        primary_focus: profile.primary_focus,
        native_language: profile.native_language,
        onboarding_completed: true,
      }));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Study settings failed to save.");
    } finally {
      setSavingSettings(false);
    }
  };

  const handlePlanReset = async () => {
    if (!window.confirm("Reset this week's study plan and its completion status?")) return;
    setResettingPlan(true);
    setActionError("");
    try {
      await api.resetStudyPlan();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Study plan failed to reset.");
    } finally {
      setResettingPlan(false);
    }
  };

  return {
    avatarInputRef,
    cropFile,
    setCropFile,
    actionError,
    savingTarget,
    savingSettings,
    savingAvatar,
    resettingPlan,
    handleAvatarSelect,
    handleCropSave,
    handleAvatarRemove,
    handleTargetChange,
    handleSettingsSave,
    handlePlanReset,
  };
}
