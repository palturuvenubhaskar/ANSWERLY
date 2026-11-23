"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { api } from "../../lib/api";
import { ExportResponse } from "../../types";
import {
  Download,
  FileText,
  FileCode,
  FileSpreadsheet,
  CheckCircle2,
  Clock,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

interface ExportFormatOption {
  format: "pdf" | "docx" | "md" | "json";
  title: string;
  description: string;
  icon: React.ElementType;
  extension: string;
}

const EXPORT_FORMATS: ExportFormatOption[] = [
  {
    format: "pdf",
    title: "Print-Ready PDF",
    description: "Styled exam-ready booklet with unit headers, marks allocation, and answer sections.",
    icon: FileText,
    extension: ".pdf",
  },
  {
    format: "docx",
    title: "Word Document (DOCX)",
    description: "Fully editable document for tailoring question explanations and student handouts.",
    icon: FileSpreadsheet,
    extension: ".docx",
  },
  {
    format: "md",
    title: "Markdown (MD)",
    description: "Lightweight notes file with GitHub-flavored markdown, formulas, and bullet structures.",
    icon: FileCode,
    extension: ".md",
  },
  {
    format: "json",
    title: "Structured JSON",
    description: "Complete canonical data schema export with verification reports and audit metadata.",
    icon: FileCode,
    extension: ".json",
  },
];

export function ExportsTab() {
  const { activeDocument, notify } = useApp();
  const [includeUnapproved, setIncludeUnapproved] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [recentExports, setRecentExports] = useState<ExportResponse[]>([]);

  const handleExport = async (format: "pdf" | "docx" | "md" | "json") => {
    if (!activeDocument) return;
    setGenerating(format);
    try {
      const exp = await api.createExport(activeDocument.id, format, undefined, includeUnapproved);
      setRecentExports((prev) => [exp, ...prev]);
      notify(`Export created: ${format.toUpperCase()}`, "success");

      // Auto download
      const filename = `${activeDocument.title.replace(/\.[^/.]+$/, "")}_answers.${format}`;
      await api.downloadExport(exp.id, filename);
      notify(`Downloaded ${filename}`, "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Export failed";
      notify(msg, "error");
    } finally {
      setGenerating(null);
    }
  };

  const handleDownloadExisting = async (exp: ExportResponse) => {
    if (!activeDocument) return;
    try {
      const filename = `${activeDocument.title.replace(/\.[^/.]+$/, "")}_export_${exp.id.substring(0, 6)}.${exp.format}`;
      await api.downloadExport(exp.id, filename);
      notify(`Downloaded ${filename}`, "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to download";
      notify(msg, "error");
    }
  };

  if (!activeDocument) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500 mb-4">
          <Download className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-semibold text-slate-200">No active document selected</h2>
        <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
          Please select a document from the Documents tab before generating exports.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-100">Multi-Format Exam Export Center</h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Export verified answers organized by unit and question position. By default, only answers with passing
              verifier checks or human approval decisions are exported.
            </p>
          </div>

          {/* Include unapproved toggle */}
          <label className="flex items-center gap-2.5 bg-slate-950 border border-slate-800 px-3.5 py-2 rounded-lg cursor-pointer hover:border-slate-700 transition-colors">
            <input
              type="checkbox"
              checked={includeUnapproved}
              onChange={(e) => setIncludeUnapproved(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
            />
            <span className="text-xs text-slate-300 font-medium">Include unapproved / draft answers</span>
          </label>
        </div>
      </div>

      {/* Export Format Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {EXPORT_FORMATS.map((fmt) => {
          const Icon = fmt.icon;
          const isBusy = generating === fmt.format;
          return (
            <div
              key={fmt.format}
              className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition-colors"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-lg bg-blue-950/70 border border-blue-800/60 flex items-center justify-center text-blue-400">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">{fmt.title}</h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{fmt.description}</p>
                </div>
              </div>

              <div className="pt-6">
                <button
                  onClick={() => handleExport(fmt.format)}
                  disabled={isBusy}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium text-xs py-2 rounded-lg transition-colors shadow-sm"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>{isBusy ? "Generating..." : `Export ${fmt.format.toUpperCase()}`}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Exports */}
      {recentExports.length > 0 && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800">
            <h3 className="text-sm font-semibold text-slate-200">Session Exports</h3>
          </div>
          <div className="divide-y divide-slate-800/60">
            {recentExports.map((exp) => (
              <div key={exp.id} className="p-4 flex items-center justify-between gap-4 text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold uppercase text-blue-400 bg-blue-950/60 border border-blue-800 px-2 py-0.5 rounded">
                    {exp.format}
                  </span>
                  <div className="text-slate-300 font-mono">ID: {exp.id}</div>
                </div>

                <button
                  onClick={() => handleDownloadExisting(exp)}
                  className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 font-medium"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Again</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
