"use client";

import type { ChangeEvent, RefObject } from "react";
import { BarChart3, LogOut } from "lucide-react";
import { mediaUrl, type UserProfile } from "@/shared/api";
import { Button, LinkButton } from "@/shared/ui";
import { routes } from "@/shared/config";

export function ProfileHeader({
  profile,
  username,
  loading,
  totalSessions,
  targetBand,
  savingAvatar,
  avatarInputRef,
  onAvatarSelect,
  onAvatarRemove,
  onLogout,
}: {
  profile: UserProfile | null;
  username: string | null;
  loading: boolean;
  totalSessions: number;
  targetBand: number;
  savingAvatar: boolean;
  avatarInputRef: RefObject<HTMLInputElement | null>;
  onAvatarSelect: (event: ChangeEvent<HTMLInputElement>) => void;
  onAvatarRemove: () => void;
  onLogout: () => void;
}) {
  return (
      <section className="animate-fade-up rounded-2xl border border-[var(--border)] bg-white p-6 shadow-sm shadow-slate-200/40">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            {profile?.avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaUrl(profile.avatar) ?? undefined}
                alt="Your avatar"
                className="h-14 w-14 rounded-full object-cover ring-2 ring-[var(--brand)]/15 ring-offset-2 ring-offset-white"
              />
            ) : (
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--brand)] text-xl font-bold text-white ring-2 ring-[var(--brand)]/15 ring-offset-2 ring-offset-white">
                {(profile?.username ?? username)?.[0]?.toUpperCase() ?? "?"}
              </span>
            )}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Profile
              </p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                {profile?.username ?? username ?? "Student"}
              </h1>
              <p className="mt-0.5 text-sm font-medium text-[var(--text-secondary)]">
                {loading
                  ? "..."
                  : `${totalSessions} session${totalSessions === 1 ? "" : "s"} · Target band ${targetBand.toFixed(1)}`}
              </p>
              {profile && (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <input
                    ref={avatarInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={onAvatarSelect}
                  />
                  <button
                    type="button"
                    disabled={savingAvatar}
                    onClick={() => avatarInputRef.current?.click()}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {savingAvatar ? "Saving..." : profile.avatar ? "Change photo" : "Upload photo"}
                  </button>
                  {profile.avatar && (
                    <button
                      type="button"
                      disabled={savingAvatar}
                      onClick={onAvatarRemove}
                      className="rounded-lg px-2 py-1.5 text-sm font-medium text-slate-500 transition hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Remove
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <LinkButton href={routes.analytics()} variant="secondary">
              <BarChart3 className="h-4 w-4" />
              Analytics
            </LinkButton>
            <Button variant="secondary" onClick={onLogout}>
              <LogOut className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        </div>
      </section>
  );
}
