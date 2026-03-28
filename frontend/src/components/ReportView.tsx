"use client";

import ReactMarkdown from "react-markdown";

export default function ReportView({ markdown }: { markdown: string }) {
  return (
    <article className="prose prose-invert prose-sm max-w-none prose-headings:text-gray-200 prose-p:text-gray-300 prose-li:text-gray-300 prose-strong:text-gray-100 prose-a:text-blue-400">
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </article>
  );
}
