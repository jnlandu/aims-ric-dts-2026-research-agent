"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listJobs, type JobResult } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

export default function HistoryPage() {
  const [jobs, setJobs] = useState<JobResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listJobs()
      .then(setJobs)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load jobs")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold">Research History</h1>

      {loading && <p className="text-sm text-gray-400">Loading…</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}

      {!loading && jobs.length === 0 && (
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-8 text-center space-y-2">
          <p className="text-gray-400">No research jobs yet.</p>
          <Link
            href="/"
            className="inline-block text-sm text-blue-400 hover:text-blue-300"
          >
            Start your first research →
          </Link>
        </div>
      )}

      <div className="space-y-3">
        {jobs.map((job) => (
          <Link
            key={job.job_id}
            href={`/job/${job.job_id}`}
            className="block rounded-lg border border-gray-700 bg-gray-900 p-4 hover:bg-gray-800 transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 space-y-1">
                <p className="text-sm font-medium text-gray-200 truncate">
                  {job.question}
                </p>
                <p className="text-xs text-gray-500 font-mono">{job.job_id}</p>
              </div>
              <StatusBadge status={job.status} />
            </div>
            {job.status === "completed" && (
              <div className="mt-2 flex gap-4 text-xs text-gray-500">
                <span>📚 {job.sources_count} sources</span>
                <span>🔗 {job.evidence_count} evidence</span>
                <span>🏷️ {job.themes_count} themes</span>
              </div>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
