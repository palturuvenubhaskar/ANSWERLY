"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";
import { api } from "../../lib/api";
import {
  QuestionItem,
  ReferenceExcerptItem,
  DocumentProgressResponse,
  ProcessingJobItem,
} from "../../types";
import {
  Cpu,
  Play,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  XCircle,
  Square,
  CheckSquare,
  ChevronRight,
  Zap,
} from "lucide-react";

export function ProcessingTab() {
  const {
    activeProject,
    activeDocument,
    setActiveTab,
    setSelectedQuestionId,
    notify,
  } = useApp();

  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [references, setReferences] = useState<ReferenceExcerptItem[]>([]);
  const [selectedQuestionIds, setSelectedQuestionIds] = useState<string[]>([]);
  const [selectedRefIds, setSelectedRefIds] = useState<string[]>([]);
  const [progress, setProgress] = useState<DocumentProgressResponse | null>(null);
  const [activeJobs, setActiveJobs] = useState<ProcessingJobItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    if (!activeDocument || !activeProject) return;
    setLoading(true);
    try {
      const qList = await api.listDocumentQuestions(activeDocument.id);
      setQuestions(qList);
      // Select all questions by default if none selected
      setSelectedQuestionIds(qList.map((q) => q.id));

      const refList = await api.listReferences(activeProject.id);
      setReferences(refList);
      setSelectedRefIds(refList.map((r) => r.id));

      const prog = await api.getDocumentProgress(activeDocument.id);
      setProgress(prog);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load processing setup";
      notify(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeDocument, activeProject]);

  // Setup SSE stream listener for live updates
  useEffect(() => {
    if (!activeDocument) return;

    const cleanup = api.listenToDocumentEvents(
      activeDocument.id,
      (updatedProgress) => {
        setProgress(updatedProgress);
      },
      (err) => {
        // SSE error handled by fallback polling
      }
    );

    return cleanup;
  }, [activeDocument]);

  const toggleSelectAll = () => {
    if (selectedQuestionIds.length === questions.length) {
      setSelectedQuestionIds([]);
    } else {
      setSelectedQuestionIds(questions.map((q) => q.id));
    }
  };

  const toggleSelectQuestion = (id: string) => {
    setSelectedQuestionIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const toggleSelectReference = (id: string) => {
    setSelectedRefIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleStartProcessing = async () => {
    if (!activeDocument) return;
    if (selectedQuestionIds.length === 0) {
      notify("Select at least one question to process", "error");
      return;
    }

    if (activeDocument.status !== "READY") {
      notify("Document extraction must be confirmed before processing", "error");
      return;
    }

    setIsProcessing(true);
    try {
      // Generate a unique idempotency key
      const idempotencyKey = `run-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const res = await api.startProcessing(
        activeDocument.id,
        idempotencyKey,
        selectedQuestionIds,
        selectedRefIds
      );

      setActiveJobs(res.jobs);
      notify(`Batch processing run initiated (${res.jobs.length} jobs)`, "success");

      // Auto execute first job or trigger parallel executions
      // For local development, sequentially execute jobs to demo live pipeline
      for (const job of res.jobs) {
        api.executeJob(job.id)
          .then((execRes) => {
            setActiveJobs((prev) =>
              prev.map((j) =>
                j.id === execRes.id
                  ? { ...j, status: execRes.status as any, revision_count: execRes.revision_count }
                  : j
              )
            );
            // Refresh progress
            api.getDocumentProgress(activeDocument.id).then(setProgress).catch(() => {});
          })
          .catch(() => {});
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start processing";
      notify(msg, "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExecuteSingleJob = async (jobId: string) => {
    try {
      notify("Executing job pipeline step...", "info");
      const res = await api.executeJob(jobId);
      setActiveJobs((prev) =>
        prev.map((j) => (j.id === res.id ? { ...j, status: res.status as any } : j))
      );
      if (activeDocument) {
        const prog = await api.getDocumentProgress(activeDocument.id);
        setProgress(prog);
      }
      notify(`Job step completed: ${res.status}`, "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Job execution failed";
      notify(msg, "error");
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await api.cancelJob(jobId);
      setActiveJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, status: "CANCELLED" } : j))
      );
      notify("Job cancellation requested", "info");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to cancel job";
      notify(msg, "error");
    }
  };

  if (!activeDocument) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500 mb-4">
          <Cpu className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-semibold text-slate-200">No active document selected</h2>
        <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
          Please upload and confirm a question-bank document in the Documents tab first.
        </p>
        <button
          onClick={() => setActiveTab("documents")}
          className="mt-4 px-4 py-2 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
        >
          Go to Documents & Extraction
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Top Banner & Control Deck */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Run Configuration */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <span>Parallel Generation & Verification Engine</span>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-blue-950/70 border border-blue-800 text-blue-300">
                  M4 / Idempotent
                </span>
              </h2>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
              Each selected question is processed through three sequential steps: <strong>Generation</strong> (marks-tailored exam answer),{" "}
              <strong>Verification</strong> (7 strict criteria evaluation), and <strong>Revision</strong> (up to 2 automatic passes on failure).
            </p>

            {/* Reference Attachment Selector */}
            {references.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-800/80">
                <div className="text-xs font-medium text-slate-300 mb-2">
                  Attach Reference Excerpts to this Run:
                </div>
                <div className="flex flex-wrap gap-2">
                  {references.map((r) => {
                    const isSelected = selectedRefIds.includes(r.id);
                    return (
                      <button
                        key={r.id}
                        onClick={() => toggleSelectReference(r.id)}
                        className={`text-xs px-2.5 py-1 rounded-md border flex items-center gap-1.5 transition-colors ${
                          isSelected
                            ? "bg-blue-950/70 border-blue-700 text-blue-300"
                            : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        {isSelected ? <CheckSquare className="w-3.5 h-3.5 text-blue-400" /> : <Square className="w-3.5 h-3.5" />}
                        <span className="truncate max-w-[150px]">{r.title}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
            <div className="text-xs text-slate-400">
              Selected <strong>{selectedQuestionIds.length}</strong> of {questions.length} questions
            </div>

            <button
              onClick={handleStartProcessing}
              disabled={isProcessing || selectedQuestionIds.length === 0}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium text-xs px-5 py-2.5 rounded-lg shadow-sm transition-colors"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isProcessing ? "Starting Run..." : "Start Batch Processing"}</span>
            </button>
          </div>
        </div>

        {/* Live SSE Progress & Status Aggregations */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Live Progress</span>
              <span className="text-xs font-mono font-semibold text-blue-400">
                {progress ? `${progress.percent}%` : "0%"}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-800 mb-4">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${progress ? progress.percent : 0}%` }}
              />
            </div>

            {/* Status breakdown grid */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">Approved</span>
                <span className="font-mono font-semibold text-emerald-400">
                  {progress?.counts.VERIFIER_APPROVED || 0}
                </span>
              </div>
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">Manual Review</span>
                <span className="font-mono font-semibold text-amber-400">
                  {progress?.counts.MANUAL_REVIEW || 0}
                </span>
              </div>
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">Generating</span>
                <span className="font-mono font-semibold text-blue-400">
                  {(progress?.counts.GENERATING || 0) + (progress?.counts.REVISING || 0)}
                </span>
              </div>
              <div className="bg-slate-950/70 p-2 rounded border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">Queued</span>
                <span className="font-mono font-semibold text-slate-300">
                  {(progress?.counts.QUEUED || 0) + (progress?.counts.PENDING || 0)}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
            <span>Server-Sent Events active</span>
            <button
              onClick={() => {
                if (activeDocument) api.getDocumentProgress(activeDocument.id).then(setProgress);
              }}
              className="hover:text-slate-300 flex items-center gap-1"
            >
              <RotateCw className="w-3 h-3" />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Questions Selection & Job Queue Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={toggleSelectAll}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 font-medium"
            >
              {selectedQuestionIds.length === questions.length ? (
                <CheckSquare className="w-4 h-4 text-blue-400" />
              ) : (
                <Square className="w-4 h-4 text-slate-500" />
              )}
              <span>Select All Questions</span>
            </button>
          </div>

          <div className="text-xs text-slate-400">
            Max 2 automated revisions enforced per architectural specification
          </div>
        </div>

        <div className="divide-y divide-slate-800/60">
          {questions.map((q) => {
            const isSelected = selectedQuestionIds.includes(q.id);
            const matchingJob = activeJobs.find((j) => j.question_id === q.id);
            const currentStatus = matchingJob ? matchingJob.status : q.status;

            return (
              <div key={q.id} className="p-4 hover:bg-slate-800/30 transition-colors flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1">
                  <button
                    onClick={() => toggleSelectQuestion(q.id)}
                    className="text-slate-400 hover:text-blue-400"
                  >
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-blue-400" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-600" />
                    )}
                  </button>

                  <span className="font-mono text-xs font-semibold text-slate-500 w-8">
                    #{q.position}
                  </span>

                  <div className="space-y-1 flex-1">
                    <p className="text-sm text-slate-200 line-clamp-1 font-medium">{q.question_text}</p>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                      {q.marks && <span>{q.marks} Marks</span>}
                      {q.bl && <span>• {q.bl}</span>}
                      {matchingJob && (
                        <span className="text-slate-500">
                          • Revisions: {matchingJob.revision_count}/2
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Status Badge */}
                <div className="flex items-center gap-3 shrink-0">
                  <span
                    className={`text-[10px] uppercase font-bold px-2.5 py-1 rounded border font-mono ${
                      currentStatus === "VERIFIER_APPROVED"
                        ? "bg-emerald-950/70 border-emerald-800 text-emerald-300"
                        : currentStatus === "MANUAL_REVIEW"
                        ? "bg-amber-950/70 border-amber-800 text-amber-300"
                        : currentStatus === "GENERATING" || currentStatus === "REVISING"
                        ? "bg-blue-950/70 border-blue-800 text-blue-300 animate-pulse"
                        : currentStatus === "CANCELLED"
                        ? "bg-rose-950/70 border-rose-800 text-rose-300"
                        : "bg-slate-800 border-slate-700 text-slate-300"
                    }`}
                  >
                    {currentStatus.replace("_", " ")}
                  </span>

                  {/* Action buttons */}
                  {matchingJob && matchingJob.status === "QUEUED" && (
                    <button
                      onClick={() => handleExecuteSingleJob(matchingJob.id)}
                      title="Run execution step"
                      className="p-1.5 rounded hover:bg-slate-800 text-blue-400"
                    >
                      <Zap className="w-3.5 h-3.5" />
                    </button>
                  )}

                  {matchingJob && (matchingJob.status === "QUEUED" || matchingJob.status === "GENERATING") && (
                    <button
                      onClick={() => handleCancelJob(matchingJob.id)}
                      title="Cancel job"
                      className="p-1.5 rounded hover:bg-slate-800 text-rose-400"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                    </button>
                  )}

                  <button
                    onClick={() => {
                      setSelectedQuestionId(q.id);
                      setActiveTab("answer-studio");
                    }}
                    title="Open in Answer Studio"
                    className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors flex items-center gap-1 text-xs"
                  >
                    <span>Inspect</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
