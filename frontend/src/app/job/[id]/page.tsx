"use client";

import { use } from "react";
import Link from "next/link";
import { useJobPoller } from "@/hooks/useJobPoller";
import StatusBadge, { StatusStepper } from "@/components/StatusBadge";
import ScoreCard from "@/components/ScoreCard";
import ReportView from "@/components/ReportView";

export default function JobPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { job, error } = useJobPoller(id);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <p className="text-sm text-red-400">{error}</p>
        <Link href="/history" className="mt-4 inline-block text-sm text-blue-400">
          ← Back to history
        </Link>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <p className="text-sm text-gray-400">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <Link
        href="/history"
        className="inline-block text-sm text-gray-400 hover:text-gray-200 transition-colors"
      >
        ← Back to history
      </Link>

      {/* Header card */}
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <p className="text-sm text-gray-400 font-mono">Job {job.job_id}</p>
            <h1 className="text-lg font-semibold text-gray-100">
              {job.question}
            </h1>
          </div>
          <StatusBadge status={job.status} />
        </div>
        <StatusStepper status={job.status} />

        {job.status === "completed" && (
          <div className="flex gap-4 text-xs text-gray-400">
            <span>📚 {job.sources_count} sources</span>
            <span>🔗 {job.evidence_count} evidence</span>
            <span>🏷️ {job.themes_count} themes</span>
          </div>
        )}
      </div>

      {/* Error */}
      {job.status === "failed" && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-300">
          <p className="font-semibold">Research failed</p>
          <p className="mt-1 text-red-400">{job.error}</p>
        </div>
      )}

      {/* Evaluation scores */}
      {job.evaluation && <ScoreCard evaluation={job.evaluation} />}

      {/* Report */}
      {job.report && (
        <div className="rounded-lg border border-gray-700 bg-gray-900 p-6">
          <ReportView markdown={job.report} />
        </div>
      )}
    </div>
  );
}
