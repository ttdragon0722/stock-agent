"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { fetchReport } from "@/lib/api";
import type { ReportInfo } from "@/lib/types";

export default function ReportsPanel({ reports }: { reports: ReportInfo[] }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const open = async (name: string) => {
    setSelected(name);
    setMarkdown("");
    setError(null);
    try {
      const res = await fetchReport(name);
      setMarkdown(res.data.markdown);
    } catch (e) {
      setError(e instanceof Error ? e.message : "讀取報告失敗");
    }
  };

  if (!reports.length)
    return <p className="text-sm text-zinc-500">尚無決策報告。</p>;

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <ul className="space-y-1 text-sm">
        {reports.map((r) => (
          <li key={r.name}>
            <button
              onClick={() => open(r.name)}
              className={`w-full truncate rounded-lg px-3 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800 ${
                selected === r.name
                  ? "bg-zinc-100 font-semibold dark:bg-zinc-800"
                  : ""
              }`}
            >
              {r.name}
            </button>
          </li>
        ))}
      </ul>
      <div className="min-h-40 rounded-xl border border-zinc-200 p-5 dark:border-zinc-700">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!selected && !error && (
          <p className="text-sm text-zinc-500">← 點選左側報告以檢視</p>
        )}
        {markdown && (
          <article className="prose prose-sm max-w-none overflow-x-auto dark:prose-invert prose-table:text-xs">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {markdown}
            </ReactMarkdown>
          </article>
        )}
      </div>
    </div>
  );
}
