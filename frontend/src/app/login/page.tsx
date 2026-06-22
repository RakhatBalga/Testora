"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login(username, password);
      login(res.access_token, username);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-sm py-8">
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-500">Log in to continue practising.</p>
      </div>
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </p>
          )}
          <Input
            label="Username"
            name="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
          <Input
            label="Password"
            name="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Logging in..." : "Log in"}
          </Button>
        </form>
      </Card>
      <p className="mt-5 text-center text-sm text-slate-500">
        No account?{" "}
        <Link href="/register" className="font-medium text-blue-600 hover:underline">
          Create one
        </Link>
      </p>
    </div>
  );
}
