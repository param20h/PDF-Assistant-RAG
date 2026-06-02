"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Clock3,
  Database,
  FileText,
  HardDrive,
  RefreshCw,
  Users,
} from "lucide-react";

import { api, CONNECTION_ERROR_MESSAGE } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";

interface AdminStats {
  total_users: number;
  total_pdfs_uploaded: number;
  average_query_response_time_ms: number;
  query_count: number;
  disk_space_usage: {
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    usage_percent: number;
    upload_dir_bytes: number;
  };
}

const formatBytes = (bytes: number) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";

  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1
  );

  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

const formatTime = (milliseconds: number) => {
  if (milliseconds >= 1000) return `${(milliseconds / 1000).toFixed(2)} s`;
  return `${Math.round(milliseconds)} ms`;
};

function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: typeof Users;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card className="min-h-36">
      <CardHeader className="grid-cols-[1fr_auto]">
        <div>
          <CardDescription>{label}</CardDescription>
          <CardTitle className="mt-2 text-3xl tabular-nums">{value}</CardTitle>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}

function AdminSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {[1, 2, 3, 4].map((item) => (
        <Card key={item} className="min-h-36">
          <CardHeader>
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-8 w-20" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-4 w-36" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function AdminPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (!user.is_admin) router.replace("/dashboard");
  }, [loading, router, user]);

  const loadStats = useCallback(async () => {
    try {
      setStatsLoading(true);
      const data = await api.get<AdminStats>("/api/v1/admin/stats");
      setStats(data);
      setLastUpdated(new Date());
      setError("");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : CONNECTION_ERROR_MESSAGE;
      setError(message);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user?.is_admin) return;

    const initialLoad = window.setTimeout(() => void loadStats(), 0);
    const interval = window.setInterval(() => void loadStats(), 10000);

    return () => {
      window.clearTimeout(initialLoad);
      window.clearInterval(interval);
    };
  }, [loadStats, user?.is_admin]);

  const diskDetail = useMemo(() => {
    if (!stats) return "";
    const disk = stats.disk_space_usage;
    return `${formatBytes(disk.used_bytes)} used of ${formatBytes(disk.total_bytes)}`;
  }, [stats]);

  if (loading || !user || !user.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse-glow w-12 h-12 rounded-full bg-primary/20" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border/50 bg-card/50 px-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/dashboard")}
            title="Back to dashboard"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15">
              <Database className="h-4 w-4 text-primary" />
            </div>
            <span className="text-sm font-semibold">Admin Metrics</span>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => void loadStats()}
          disabled={statsLoading}
        >
          <RefreshCw className={statsLoading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Refresh
        </Button>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-normal">System overview</h1>
          <p className="text-sm text-muted-foreground">
            {lastUpdated
              ? `Last updated ${lastUpdated.toLocaleTimeString()}`
              : "Waiting for live metrics"}
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        {statsLoading && !stats ? (
          <AdminSkeleton />
        ) : stats ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                icon={Users}
                label="Total users"
                value={stats.total_users.toLocaleString()}
                detail="Registered accounts"
              />
              <MetricCard
                icon={FileText}
                label="PDFs uploaded"
                value={stats.total_pdfs_uploaded.toLocaleString()}
                detail="All uploaded PDF records"
              />
              <MetricCard
                icon={Clock3}
                label="Avg response time"
                value={formatTime(stats.average_query_response_time_ms)}
                detail={`${stats.query_count.toLocaleString()} measured queries`}
              />
              <MetricCard
                icon={HardDrive}
                label="Upload storage"
                value={formatBytes(stats.disk_space_usage.upload_dir_bytes)}
                detail="Files in the upload directory"
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Disk space usage</CardTitle>
                <CardDescription>{diskDetail}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Progress value={stats.disk_space_usage.usage_percent} />
                <div className="grid gap-3 text-sm sm:grid-cols-3">
                  <div>
                    <p className="text-muted-foreground">Used</p>
                    <p className="font-medium tabular-nums">
                      {formatBytes(stats.disk_space_usage.used_bytes)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Free</p>
                    <p className="font-medium tabular-nums">
                      {formatBytes(stats.disk_space_usage.free_bytes)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Usage</p>
                    <p className="font-medium tabular-nums">
                      {stats.disk_space_usage.usage_percent.toFixed(2)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        ) : null}
      </main>
    </div>
  );
}
