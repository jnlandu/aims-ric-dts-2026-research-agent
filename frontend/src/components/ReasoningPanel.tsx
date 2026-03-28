"use client";

import { useState, useEffect } from "react";
import { getReasoning, type ReasoningStep } from "@/lib/api";

const STAGE_ICONS: Record<string, string> = {
  search: "🔍",
  synthesis: "🧠",
  report: "📝",
  evaluation: "✅",
};

const STAGE_COLORS: Record<string, string> = {
  search: "border-blue-700 bg-blue-900/20",
  synthesis: "border-purple-700 bg-purple-900/20",
  report: "border-amber-700 bg-amber-900/20",
  evaluation: "border-cyan-700 bg-cyan-900/20",
};

function StepCard({ step }: { step: ReasoningStep }) {
  const [expanded, setExpanded] = useState(false);
  const icon = STAGE_ICONS[step.stage] || "📋";
  const colorClass = STAGE_COLORS[step.stage] || "border-gray-700 bg-gray-900/20";

  const renderData = () => {
    const data = step.data;

    // String list (search queries, report outline)
    if (Array.isArray(data) && data.length > 0 && typeof data[0] === "string") {
      return (
        <ul className="space-y-1 text-xs text-gray-300">
          {(data as string[]).map((item, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-gray-500 shrink-0">{i + 1}.</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      );
    }

    // Plain string (evaluation reasoning)
    if (typeof data === "string") {
      return <p className="text-xs text-gray-300 whitespace-pre-wrap">{data}</p>;
    }

    // Object arrays (sources, evidence, themes, contradictions)
    if (Array.isArray(data) && data.length > 0 && typeof data[0] === "object") {
      return (
        <div className="space-y-2">
          {(data as Record<string, unknown>[]).map((item, i) => (
            <div
              key={i}
              className="rounded border border-gray-700/50 bg-gray-800/30 p-2 text-xs space-y-1"
            >
              {Object.entries(item).map(([key, value]) => {
                if (value === "" || value === null || (Array.isArray(value) && value.length === 0))
                  return null;
                return (
                  <div key={key} className="flex gap-2">
                    <span className="text-gray-500 shrink-0 font-mono">
                      {key}:
                    </span>
                    <span className="text-gray-300 break-all">
                      {typeof value === "string"
                        ? value.length > 200
                          ? value.slice(0, 200) + "…"
                          : value
                        : JSON.stringify(value)}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      );
    }

    return (
      <pre className="text-xs text-gray-400 overflow-x-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  };

  return (
    <div className={`rounded-lg border p-3 ${colorClass}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <div>
            <p className="text-sm font-medium text-gray-200">{step.title}</p>
            <p className="text-xs text-gray-400">{step.description}</p>
          </div>
        </div>
        <span className="text-gray-500 text-xs shrink-0">
          {expanded ? "▲" : "▼"}
        </span>
      </button>
      {expanded && <div className="mt-3 pt-3 border-t border-gray-700/50">{renderData()}</div>}
    </div>
  );
}

export default function ReasoningPanel({ jobId }: { jobId: string }) {
  const [steps, setSteps] = useState<ReasoningStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    getReasoning(jobId)
      .then((res) => {
        setSteps(res.steps);
        setAvailable(res.available);
      })
      .catch(() => setAvailable(false))
      .finally(() => setLoading(false));
  }, [jobId]);

  if (loading) {
    return <p className="text-xs text-gray-500">Loading reasoning steps…</p>;
  }

  if (!available || steps.length === 0) {
    return (
      <p className="text-xs text-gray-500">
        Reasoning data not available for this job.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {steps.map((step, i) => (
        <StepCard key={i} step={step} />
      ))}
    </div>
  );
}
