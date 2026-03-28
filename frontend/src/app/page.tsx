"use client";

import { useState, FormEvent } from "react";
import { submitResearch } from "@/lib/api";
import { useJobPoller } from "@/hooks/useJobPoller";
import StatusBadge, { StatusStepper } from "@/components/StatusBadge";
import ScoreCard from "@/components/ScoreCard";
import ReportView from "@/components/ReportView";

export default function HomePage() {
  const [question, setQuestion] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { job, error: pollError } = useJobPoller(jobId);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setSubmitting(true);
    setSubmitError(null);
    setJobId(null);

    try {
      const res = await submitResearch(question.trim());
      setJobId(res.job_id);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to submit research"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleNewResearch = () => {
    setJobId(null);
    setQuestion("");
    setSubmitError(null);
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-8">
      {/* ── Submit form ──────────────────────────────────────────────── */}
      <section className="space-y-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold">New Research</h1>
          <p className="text-sm text-gray-400">
            Ask a research question and our AI agents will search, synthesise,
            and write a report.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What are the trade-offs between CNNs and Vision Transformers?"
            disabled={submitting || (!!jobId && job?.status !== "completed" && job?.status !== "failed")}
            className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={submitting || !question.trim() || (!!jobId && job?.status !== "completed" && job?.status !== "failed")}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Submitting…" : "Research"}
          </button>
        </form>

        {submitError && (
          <p className="text-sm text-red-400">Error: {submitError}</p>
        )}
      </section>

      {/* ── Job progress ─────────────────────────────────────────────── */}
      {job && (
        <section className="space-y-6">
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-5 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 min-w-0">
                <p className="text-sm text-gray-400 font-mono">
                  Job {job.job_id}
                </p>
                <p className="text-sm text-gray-300 truncate">
                  {job.question}
                </p>
              </div>
              <StatusBadge status={job.status} />
            </div>
            <StatusStepper status={job.status} />

            {/* Stats row */}
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

          {/* New research */}
          {(job.status === "completed" || job.status === "failed") && (
            <button
              onClick={handleNewResearch}
              className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 transition-colors"
            >
              ← Start new research
            </button>
          )}
        </section>
      )}

      {pollError && (
        <p className="text-sm text-red-400">Polling error: {pollError}</p>
      )}
    </div>
  );
}
