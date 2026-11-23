"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";
import { api } from "../../lib/api";
import {
  QuestionItem,
  LatestAnswerResponse,
  AnswerVersionItem,
  AnswerContent,
  VerificationReport,
} from "../../types";
import {
  GraduationCap,
  CheckCircle2,
  XCircle,
  AlertCircle,
  HelpCircle,
  Edit3,
  RotateCw,
  Clock,
  ShieldCheck,
  ChevronRight,
  BookOpen,
  Code,
  FileText,
  UserCheck,
  Play,
} from "lucide-react";

export function AnswerStudioTab() {
  const {
    activeDocument,
    selectedQuestionId,
    setSelectedQuestionId,
    setActiveTab,
    notify,
  } = useApp();

  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [activeQuestion, setActiveQuestion] = useState<QuestionItem | null>(null);
  const [answerData, setAnswerData] = useState<LatestAnswerResponse | null>(null);
  const [versions, setVersions] = useState<AnswerVersionItem[]>([]);
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [activeVersionNumber, setActiveVersionNumber] = useState<number | null>(null);

  // Edit Answer Modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editIntro, setEditIntro] = useState("");
  const [editConclusion, setEditConclusion] = useState("");
  const [editSections, setEditSections] = useState<
    Array<{ heading: string; content: string; bullets: string[]; formula?: string | null; example?: string | null }>
  >([]);
  const [savingEdit, setSavingEdit] = useState(false);

  // Filter state
  const [filter, setFilter] = useState<"ALL" | "APPROVED" | "REVIEW">("ALL");

  const loadQuestions = async () => {
    if (!activeDocument) return;
    try {
      const qList = await api.listDocumentQuestions(activeDocument.id);
      setQuestions(qList);

      if (qList.length > 0) {
        const targetId = selectedQuestionId || qList[0].id;
        const found = qList.find((q) => q.id === targetId) || qList[0];
        setActiveQuestion(found);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load questions";
      notify(msg, "error");
    }
  };

  useEffect(() => {
    loadQuestions();
  }, [activeDocument]);

  const loadAnswerForQuestion = async (qId: string) => {
    setLoadingAnswer(true);
    try {
      const latest = await api.getLatestAnswer(qId);
      setAnswerData(latest);
      setActiveVersionNumber(latest.version_number);

      const verList = await api.getAnswerVersions(qId);
      setVersions(verList);
    } catch {
      // No answer generated yet
      setAnswerData(null);
      setVersions([]);
    } finally {
      setLoadingAnswer(false);
    }
  };

  useEffect(() => {
    if (activeQuestion) {
      loadAnswerForQuestion(activeQuestion.id);
    }
  }, [activeQuestion]);

  const handleApprove = async () => {
    if (!activeQuestion || !answerData) return;
    try {
      await api.recordApproval(activeQuestion.id, answerData.answer_version_id, "APPROVED");
      notify("Human decision recorded: APPROVED for this answer version", "success");
      await loadAnswerForQuestion(activeQuestion.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record approval";
      notify(msg, "error");
    }
  };

  const handleReject = async () => {
    if (!activeQuestion || !answerData) return;
    try {
      await api.recordApproval(activeQuestion.id, answerData.answer_version_id, "REJECTED");
      notify("Human decision recorded: REJECTED", "info");
      await loadAnswerForQuestion(activeQuestion.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record rejection";
      notify(msg, "error");
    }
  };

  const handleRegenerate = async () => {
    if (!activeQuestion) return;
    try {
      const res = await api.regenerateQuestion(activeQuestion.id);
      notify("Regeneration run queued", "info");
      // execute directly in local dev
      await api.executeJob(res.job_id);
      await loadAnswerForQuestion(activeQuestion.id);
      notify("New answer version generated and verified!", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to regenerate";
      notify(msg, "error");
    }
  };

  const openEditAnswerModal = () => {
    if (!answerData) return;
    setEditIntro(answerData.answer.introduction || "");
    setEditConclusion(answerData.answer.conclusion || "");
    setEditSections(
      answerData.answer.sections.map((s) => ({
        heading: s.heading,
        content: s.content,
        bullets: s.bullets || [],
        formula: s.formula || null,
        example: s.example || null,
      }))
    );
    setIsEditModalOpen(true);
  };

  const handleSaveEditAsNewVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeQuestion) return;
    setSavingEdit(true);
    try {
      const newAnswerContent: AnswerContent = {
        introduction: editIntro,
        sections: editSections,
        conclusion: editConclusion,
      };
      await api.saveAnswerEdit(activeQuestion.id, newAnswerContent);
      setIsEditModalOpen(false);
      notify("User edits saved as a new immutable version", "success");
      await loadAnswerForQuestion(activeQuestion.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save answer edit";
      notify(msg, "error");
    } finally {
      setSavingEdit(false);
    }
  };

  if (!activeDocument) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500 mb-4">
          <GraduationCap className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-semibold text-slate-200">No document loaded</h2>
        <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
          Please upload and extract questions first in the Documents tab.
        </p>
      </div>
    );
  }

  // Filter questions
  const filteredQuestions = questions.filter((q) => {
    if (filter === "APPROVED") return q.status === "VERIFIER_APPROVED";
    if (filter === "REVIEW") return q.status === "MANUAL_REVIEW";
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Questions Navigator (3 cols) */}
        <div className="lg:col-span-3 bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden sticky top-20">
          <div className="p-3 border-b border-slate-800 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-200">Questions Navigator</span>
            <div className="flex gap-1">
              <button
                onClick={() => setFilter("ALL")}
                className={`text-[10px] px-2 py-0.5 rounded ${
                  filter === "ALL" ? "bg-blue-600 text-white font-medium" : "text-slate-400 hover:text-white"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilter("APPROVED")}
                className={`text-[10px] px-2 py-0.5 rounded ${
                  filter === "APPROVED" ? "bg-emerald-600 text-white font-medium" : "text-slate-400 hover:text-white"
                }`}
              >
                Approved
              </button>
            </div>
          </div>

          <div className="max-h-[calc(100vh-200px)] overflow-y-auto divide-y divide-slate-800/60">
            {filteredQuestions.map((q) => {
              const isSelected = activeQuestion?.id === q.id;
              return (
                <button
                  key={q.id}
                  onClick={() => {
                    setActiveQuestion(q);
                    setSelectedQuestionId(q.id);
                  }}
                  className={`w-full text-left p-3 text-xs transition-colors block ${
                    isSelected ? "bg-blue-950/40 border-l-2 border-blue-500" : "hover:bg-slate-800/40"
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                    <span className="font-mono font-semibold">#{q.position}</span>
                    {q.marks && (
                      <span className="font-mono text-blue-400 bg-blue-950/60 px-1.5 py-0.2 rounded border border-blue-800/50">
                        {q.marks}M
                      </span>
                    )}
                  </div>
                  <p className="text-slate-200 font-medium line-clamp-2 leading-snug">{q.question_text}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Center Column: Structured Answer Canvas (6 cols) */}
        <div className="lg:col-span-6 space-y-6">
          {activeQuestion && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
              {/* Question Header & Provenance */}
              <div className="border-b border-slate-800 pb-4 mb-6">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-xs font-bold text-blue-400 bg-blue-950/70 border border-blue-800/60 px-2 py-0.5 rounded">
                    Question #{activeQuestion.position}
                  </span>
                  {activeQuestion.marks && (
                    <span className="font-mono text-xs text-slate-300 bg-slate-800 px-2 py-0.5 rounded">
                      {activeQuestion.marks} Marks
                    </span>
                  )}
                  {activeQuestion.bl && (
                    <span className="font-mono text-xs text-purple-300 bg-purple-950/60 border border-purple-800/50 px-2 py-0.5 rounded">
                      {activeQuestion.bl}
                    </span>
                  )}
                  {activeQuestion.co && (
                    <span className="font-mono text-xs text-indigo-300 bg-indigo-950/60 border border-indigo-800/50 px-2 py-0.5 rounded">
                      {activeQuestion.co}
                    </span>
                  )}
                </div>

                <h3 className="text-base font-semibold text-slate-100 leading-snug">
                  {activeQuestion.question_text}
                </h3>
              </div>

              {/* Answer Content */}
              {loadingAnswer ? (
                <div className="py-12 text-center text-xs text-slate-400">Loading structured answer...</div>
              ) : !answerData ? (
                <div className="py-12 text-center space-y-3">
                  <p className="text-xs text-slate-400">No answer generated for this question yet.</p>
                  <button
                    onClick={handleRegenerate}
                    className="inline-flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg transition-colors"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Generate Answer Now</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-6 text-sm text-slate-200 leading-relaxed">
                  {/* Introduction */}
                  {answerData.answer.introduction && (
                    <div className="font-serif italic text-slate-300 border-l-2 border-slate-700 pl-4 py-0.5">
                      {answerData.answer.introduction}
                    </div>
                  )}

                  {/* Sections */}
                  {answerData.answer.sections.map((sec, idx) => (
                    <div key={idx} className="space-y-3 pt-3">
                      <h4 className="text-sm font-bold text-slate-100 tracking-wide flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                        <span>{sec.heading}</span>
                      </h4>

                      <p className="text-slate-300 leading-relaxed font-normal">{sec.content}</p>

                      {/* Bullets */}
                      {sec.bullets && sec.bullets.length > 0 && (
                        <ul className="space-y-1.5 pl-4 list-disc text-slate-300 text-xs">
                          {sec.bullets.map((b, bIdx) => (
                            <li key={bIdx} className="leading-relaxed">{b}</li>
                          ))}
                        </ul>
                      )}

                      {/* Formula Callout */}
                      {sec.formula && (
                        <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-blue-300">
                          <div className="text-[10px] uppercase text-slate-500 font-sans font-semibold mb-1">
                            Formula / Law
                          </div>
                          <div className="overflow-x-auto">{sec.formula}</div>
                        </div>
                      )}

                      {/* Example Callout */}
                      {sec.example && (
                        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs text-slate-300">
                          <div className="text-[10px] uppercase text-emerald-400 font-semibold mb-1">
                            Concrete Example
                          </div>
                          <div>{sec.example}</div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Conclusion */}
                  {answerData.answer.conclusion && (
                    <div className="pt-4 border-t border-slate-800/80 text-xs text-slate-300">
                      <strong>Summary:</strong> {answerData.answer.conclusion}
                    </div>
                  )}

                  {/* Mermaid Diagram source if present */}
                  {answerData.answer.diagram_source && (
                    <div className="mt-4 bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-300">
                      <div className="text-[10px] uppercase text-slate-500 font-sans font-semibold mb-1">
                        Mermaid Diagram Structure
                      </div>
                      <pre className="overflow-x-auto text-[11px] text-slate-400">{answerData.answer.diagram_source}</pre>
                    </div>
                  )}

                  {/* Human Decision Toolbar */}
                  <div className="mt-8 pt-4 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleApprove}
                        className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs px-3.5 py-2 rounded-lg transition-colors shadow-sm"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approve Answer</span>
                      </button>

                      <button
                        onClick={handleReject}
                        className="flex items-center gap-1.5 bg-slate-800 hover:bg-rose-950/60 text-slate-300 hover:text-rose-300 font-medium text-xs px-3.5 py-2 rounded-lg transition-colors border border-slate-700"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>

                      <button
                        onClick={openEditAnswerModal}
                        className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs px-3.5 py-2 rounded-lg transition-colors border border-slate-700"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Edit (New Version)</span>
                      </button>
                    </div>

                    <button
                      onClick={handleRegenerate}
                      title="Trigger new generation run"
                      className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white"
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                      <span>Regenerate</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Verifier 7-Criteria Inspector & Version Timeline (3 cols) */}
        <div className="lg:col-span-3 space-y-6">
          {/* Verifier Verdict Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-blue-400" />
                <span>Verifier Inspection</span>
              </span>
              {answerData?.verifier_report && (
                <span
                  className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                    answerData.verifier_report.verdict === "approved"
                      ? "bg-emerald-950/70 border-emerald-800 text-emerald-300"
                      : "bg-amber-950/70 border-amber-800 text-amber-300"
                  }`}
                >
                  {answerData.verifier_report.verdict.replace("_", " ")}
                </span>
              )}
            </div>

            {/* 7 Strict Criteria Matrix */}
            {answerData?.verifier_report?.criteria ? (
              <div className="space-y-2 pt-2">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  7 Required Criteria
                </div>
                {answerData.verifier_report.criteria.map((c, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded bg-slate-950 border border-slate-850 flex items-start justify-between gap-2 text-xs"
                  >
                    <div>
                      <div className="font-medium text-slate-200 capitalize">
                        {c.name.replace("_", " ")}
                      </div>
                      {c.notes && (
                        <div className="text-[11px] text-slate-400 mt-0.5">{c.notes}</div>
                      )}
                    </div>
                    <span
                      className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded font-mono shrink-0 ${
                        c.status === "pass"
                          ? "bg-emerald-950 border border-emerald-800 text-emerald-400"
                          : c.status === "fail"
                          ? "bg-rose-950 border border-rose-800 text-rose-400"
                          : "bg-amber-950 border border-amber-800 text-amber-400"
                      }`}
                    >
                      {c.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 py-3 italic">
                No verifier report generated for this version yet.
              </div>
            )}

            {/* Issues breakdown */}
            {answerData?.verifier_report?.issues && answerData.verifier_report.issues.length > 0 && (
              <div className="space-y-2 pt-3 border-t border-slate-800">
                <div className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">
                  Flagged Issues ({answerData.verifier_report.issues.length})
                </div>
                {answerData.verifier_report.issues.map((iss, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-amber-950/20 border border-amber-900/40 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-amber-300 capitalize">{iss.category}</span>
                      <span className="text-[9px] font-mono uppercase bg-amber-950 text-amber-300 px-1.5 py-0.5 rounded border border-amber-800">
                        {iss.severity}
                      </span>
                    </div>
                    <p className="text-slate-300 text-[11px]">{iss.description}</p>
                    {iss.required_action && (
                      <p className="text-[11px] text-amber-400/90 font-medium">
                        Action: {iss.required_action}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Version Timeline Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-slate-400" />
              <span>Immutable Version History</span>
            </span>

            {versions.length === 0 ? (
              <div className="text-xs text-slate-500 italic py-2">No past versions.</div>
            ) : (
              <div className="space-y-2">
                {versions.map((ver) => (
                  <div
                    key={ver.id}
                    className={`p-2.5 rounded border text-xs flex items-center justify-between ${
                      activeVersionNumber === ver.version_number
                        ? "bg-blue-950/40 border-blue-800 text-blue-200"
                        : "bg-slate-950 border-slate-850 text-slate-400"
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-slate-200">Version {ver.version_number}</div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        {ver.provider || "AI"} · {ver.model || "default"}
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      {ver.human_approvals && ver.human_approvals.length > 0 && (
                        <span className="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">
                          {ver.human_approvals[ver.human_approvals.length - 1].decision}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Edit Answer Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="pb-3 border-b border-slate-800">
              <h3 className="text-base font-semibold text-slate-100">Edit Answer</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Edits are saved as a new version with your human provenance. The previous versions remain archived.
              </p>
            </div>

            <form onSubmit={handleSaveEditAsNewVersion} className="overflow-y-auto py-4 space-y-4 flex-1">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Opening Paragraph / Intro</label>
                <textarea
                  rows={2}
                  value={editIntro}
                  onChange={(e) => setEditIntro(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              {editSections.map((sec, idx) => (
                <div key={idx} className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                  <div className="text-xs font-semibold text-slate-300">Section {idx + 1}</div>
                  <input
                    type="text"
                    placeholder="Heading"
                    value={sec.heading}
                    onChange={(e) => {
                      const updated = [...editSections];
                      updated[idx].heading = e.target.value;
                      setEditSections(updated);
                    }}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-100 font-medium"
                  />
                  <textarea
                    rows={3}
                    placeholder="Content explanation"
                    value={sec.content}
                    onChange={(e) => {
                      const updated = [...editSections];
                      updated[idx].content = e.target.value;
                      setEditSections(updated);
                    }}
                    className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-slate-100"
                  />
                </div>
              ))}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Conclusion Summary</label>
                <textarea
                  rows={2}
                  value={editConclusion}
                  onChange={(e) => setEditConclusion(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingEdit}
                  className="px-4 py-2 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                >
                  {savingEdit ? "Saving New Version..." : "Save as New Version"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
