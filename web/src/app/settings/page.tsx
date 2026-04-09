"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Shield,
  User,
  HardDrive,
  Sparkles,
  Trash2,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-white p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function ProfileSection() {
  const { user, authEnabled } = useAuth();
  if (!user) return null;

  return (
    <Section title="Profile" icon={User}>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Email</span>
          <div className="flex items-center gap-2">
            <span className="text-sm">{user.email}</span>
            {user.email_verified && (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700">
                <CheckCircle2 className="h-3 w-3" />
                Verified
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Plan</span>
          <span className="inline-flex rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
            {user.plan}
          </span>
        </div>
        {user.created_at && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Member since</span>
            <span className="text-sm">
              {new Date(user.created_at).toLocaleDateString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </span>
          </div>
        )}
        {!authEnabled && (
          <p className="text-xs text-muted-foreground italic">
            Running in local mode. Enable auth for multi-user support.
          </p>
        )}
      </div>
    </Section>
  );
}

function SecuritySection() {
  const { authEnabled } = useAuth();
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  if (!authEnabled) return null;

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    if (newPw !== confirmPw) {
      setMessage({ type: "error", text: "New passwords don't match" });
      return;
    }
    setLoading(true);
    try {
      const res = await api.auth.changePassword(currentPw, newPw);
      setMessage({ type: "success", text: res.message });
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to change password";
      const match = msg.match(/API \d+: (.*)/);
      const detail = match ? (JSON.parse(match[1])?.detail ?? msg) : msg;
      setMessage({ type: "error", text: detail });
    }
    setLoading(false);
  };

  return (
    <Section title="Security" icon={Shield}>
      <form onSubmit={handleChangePassword} className="space-y-3">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Change Password
        </h3>

        {message && (
          <div
            className={`rounded-lg px-3 py-2 text-sm ${
              message.type === "success"
                ? "border border-green-200 bg-green-50 text-green-800"
                : "border border-destructive/30 bg-destructive/5 text-destructive"
            }`}
          >
            {message.text}
          </div>
        )}

        <input
          type="password"
          value={currentPw}
          onChange={(e) => setCurrentPw(e.target.value)}
          placeholder="Current password"
          required
          className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        />
        <input
          type="password"
          value={newPw}
          onChange={(e) => setNewPw(e.target.value)}
          placeholder="New password (min 8 chars, 1 letter + 1 digit)"
          required
          minLength={8}
          className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        />
        <input
          type="password"
          value={confirmPw}
          onChange={(e) => setConfirmPw(e.target.value)}
          placeholder="Confirm new password"
          required
          className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Changing...
            </span>
          ) : (
            "Change password"
          )}
        </button>
      </form>
    </Section>
  );
}

function AISection() {
  const { data: aiInfo } = useQuery({
    queryKey: ["ai-info"],
    queryFn: () => api.aiInfo(),
  });

  const models = aiInfo?.models ?? [];
  if (models.length === 0) return null;

  return (
    <Section title="AI Models" icon={Sparkles}>
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          Available models for search and summarization:
        </p>
        <div className="space-y-1.5">
          {models.map((m) => (
            <div
              key={m.id}
              className="flex items-center justify-between rounded-md border border-border px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{m.model}</span>
                {m.id === aiInfo?.default && (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                    default
                  </span>
                )}
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  m.local
                    ? "bg-green-50 text-green-700"
                    : "bg-blue-50 text-blue-700"
                }`}
              >
                {m.local ? "local" : m.provider}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}

function StatsSection() {
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => api.stats(),
  });

  return (
    <Section title="Storage" icon={HardDrive}>
      {stats ? (
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-2xl font-semibold">{stats.papers}</p>
            <p className="text-xs text-muted-foreground">Papers</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-semibold">{stats.collections}</p>
            <p className="text-xs text-muted-foreground">Collections</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-semibold">{stats.storage_mb}</p>
            <p className="text-xs text-muted-foreground">MB used</p>
          </div>
        </div>
      ) : (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      )}
    </Section>
  );
}

function DangerSection() {
  const { authEnabled, logout } = useAuth();
  const router = useRouter();
  const [showConfirm, setShowConfirm] = useState(false);
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.auth.deleteAccount(password);
      router.push("/login");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed";
      const match = msg.match(/API \d+: (.*)/);
      setError(match ? (JSON.parse(match[1])?.detail ?? msg) : msg);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-3">
      <button
        onClick={async () => { await logout(); router.push("/login"); }}
        className="w-full rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted transition-colors"
      >
        Log out
      </button>

      {authEnabled && (
        <>
          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="w-full rounded-lg border border-destructive/30 px-4 py-2 text-sm font-medium text-destructive hover:bg-destructive/5 transition-colors"
            >
              <span className="flex items-center justify-center gap-2">
                <Trash2 className="h-4 w-4" />
                Delete account
              </span>
            </button>
          ) : (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertTriangle className="h-4 w-4" />
                <strong>This action is irreversible</strong>
              </div>
              <p className="text-xs text-muted-foreground">
                All your papers, collections, and searches will be permanently deleted.
                Enter your password to confirm.
              </p>
              {error && (
                <p className="text-xs text-destructive">{error}</p>
              )}
              <form onSubmit={handleDelete} className="flex gap-2">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Your password"
                  required
                  className="flex-1 rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-destructive/30"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-white hover:bg-destructive/90 disabled:opacity-50 transition-colors"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Delete"}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowConfirm(false); setPassword(""); setError(null); }}
                  className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
              </form>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-white sticky top-0 z-10">
        <div className="flex items-center gap-4 px-6 py-3 max-w-2xl mx-auto">
          <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="text-lg font-light tracking-tight">
            Ref<span className="text-primary font-normal">Lens</span>
            <span className="text-muted-foreground ml-2 text-sm">Settings</span>
          </h1>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        <ProfileSection />
        <SecuritySection />
        <AISection />
        <StatsSection />
        <DangerSection />
      </div>
    </div>
  );
}
