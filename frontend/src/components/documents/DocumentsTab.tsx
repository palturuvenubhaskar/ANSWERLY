"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "../../context/AppContext";
import { api } from "../../lib/api";
import { DocumentItem, QuestionItem, DuplicateItem } from "../../types";
import {
  Upload,
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  Edit2,
  Trash2,
  RefreshCw,
  Copy,
  ChevronRight,
  Eye,
  Check,
  Hash,
  BookOpen,
} from "lucide-react";

export function DocumentsTab() {
  const {
    activeProject,
    activeDocument,
    setActiveDocument,
    setActiveTab,
    setSelectedQuestionId,
    notify,
  } = useApp();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicateItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [showOriginalMap, setShowOriginalMap] = useState<Record<string, boolean>>({});
  const [editingQuestion, setEditingQuestion] = useState<QuestionItem | null>(null);
  const [showDuplicatesModal, setShowDuplicatesModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Edit form state
  const [editText, setEditText] = useState("");
  const [editMarks, setEditMarks] = useState<string>("");
  const [editBL, setEditBL] = useState("");
  const [editCO, setEditCO] = useState("");

  const loadDocumentQuestions = async (docId: string) => {
    setLoadingQuestions(true);
    try {
      const qList = await api.listDocumentQuestions(docId);
      setQuestions(qList);
      const dupes = await api.getDocumentDuplicates(docId);
      setDuplicates(dupes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load questions";
      notify(msg, "error");
    } finally {
      setLoadingQuestions(false);
    }
  };

  useEffect(() => {
    if (activeDocument) {
      loadDocumentQuestions(activeDocument.id);
    } else {
      setQuestions([]);
      setDuplicates([]);
    }
  }, [activeDocument]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeProject) return;

    if (file.size > 31457280) {
      notify("File size exceeds 30 MB limit", "error");
      return;
    }

    setUploading(true);
    try {
      const doc = await api.uploadDocument(activeProject.id, file);
      notify(`Uploaded "${file.name}" and extracted questions`, "success");
      setActiveDocument(doc);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload document";
      notify(msg, "error");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleConfirmExtraction = async () => {
    if (!activeDocument) return;
    try {
      const res = await api.confirmExtraction(activeDocument.id);
      setActiveDocument({ ...activeDocument, status: res.status });
      notify("Extraction confirmed. Document is ready for processing!", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to confirm extraction";
      notify(msg, "error");
    }
  };

  const handleRetryExtraction = async () => {
    if (!activeDocument) return;
    try {
      const res = await api.extractDocument(activeDocument.id);
      setActiveDocument({
        ...activeDocument,
        status: res.status,
        extraction_warnings: res.extraction_warnings,
      });
      await loadDocumentQuestions(activeDocument.id);
      notify("Extraction re-executed successfully", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to re-extract";
      notify(msg, "error");
    }
  };

  const openEditModal = (q: QuestionItem) => {
    setEditingQuestion(q);
    setEditText(q.question_text);
    setEditMarks(q.marks !== null && q.marks !== undefined ? String(q.marks) : "");
    setEditBL(q.bl || "");
    setEditCO(q.co || "");
  };

  const handleSaveQuestionEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingQuestion) return;
    try {
      const updated = await api.updateQuestion(editingQuestion.id, {
        question_text: editText.trim(),
        marks: editMarks.trim() ? parseInt(editMarks.trim(), 10) : null,
        bl: editBL.trim() || null,
        co: editCO.trim() || null,
      });
      setQuestions((prev) =>
        prev.map((item) => (item.id === updated.id ? { ...item, ...updated } : item))
      );
      setEditingQuestion(null);
      notify("Question updated (original text preserved for auditing)", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update question";
      notify(msg, "error");
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500 mb-4">
          <FileText className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-semibold text-slate-200">No project selected</h2>
        <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
          Create or select a project from the top bar to upload question banks and inspect extractions.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Top Header & Dropzone */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Zone */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-6 relative overflow-hidden">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
            <div>
              <h2 className="text-base font-semibold text-slate-100">Upload Question Bank</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Accepts multi-page PDF or DOCX files up to 30 MB. Preserves units, marks, and BL/CO tags.
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs px-4 py-2.5 rounded-lg shadow-sm transition-colors whitespace-nowrap"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>{uploading ? "Extracting Questions..." : "Select PDF / DOCX"}</span>
            </button>
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-800 hover:border-slate-700 bg-slate-950/40 rounded-lg p-6 text-center cursor-pointer transition-colors"
          >
            <div className="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center mx-auto text-slate-400 mb-2">
              <Upload className="w-5 h-5 text-blue-400" />
            </div>
            <p className="text-xs font-medium text-slate-300">
              Drag and drop syllabus question bank or past exam papers here
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              PyMuPDF engine with scanned OCR fallback and SHA-256 integrity verification
            </p>
          </div>
        </div>

        {/* Active Document Status Card */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Document</span>
              {activeDocument && (
                <span
                  className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                    activeDocument.status === "READY"
                      ? "bg-emerald-950/70 border-emerald-800 text-emerald-300"
                      : activeDocument.status === "REVIEW_REQUIRED"
                      ? "bg-amber-950/70 border-amber-800 text-amber-300"
                      : "bg-slate-800 border-slate-700 text-slate-300"
                  }`}
                >
                  {activeDocument.status.replace("_", " ")}
                </span>
              )}
            </div>

            {activeDocument ? (
              <div className="space-y-2">
                <div className="text-sm font-semibold text-slate-100 truncate" title={activeDocument.title}>
                  {activeDocument.title}
                </div>
                <div className="text-xs text-slate-400 flex items-center gap-3">
                  <span>{(activeDocument.file_size_bytes / 1024).toFixed(1)} KB</span>
                  <span>•</span>
                  <span>{questions.length} questions extracted</span>
                </div>
                <div className="text-[11px] font-mono text-slate-500 truncate" title={activeDocument.sha256}>
                  SHA256: {activeDocument.sha256.substring(0, 16)}...
                </div>
              </div>
            ) : (
              <div className="text-xs text-slate-500 italic py-3">
                No document loaded. Upload a document to start extracting questions.
              </div>
            )}
          </div>

          {activeDocument && (
            <div className="pt-4 border-t border-slate-800 flex items-center gap-2">
              {activeDocument.status !== "READY" ? (
                <button
                  onClick={handleConfirmExtraction}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium py-2 rounded-lg transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Confirm Extraction</span>
                </button>
              ) : (
                <button
                  onClick={() => setActiveTab("processing")}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium py-2 rounded-lg transition-colors"
                >
                  <span>Go to Processing</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={handleRetryExtraction}
                title="Re-run extraction"
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Warnings & Duplicates Banner */}
      {activeDocument && (
        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 border border-slate-800/80 rounded-lg p-3 text-xs">
          <div className="flex items-center gap-4">
            {activeDocument.extraction_warnings && activeDocument.extraction_warnings.length > 0 ? (
              <div className="flex items-center gap-1.5 text-amber-400">
                <AlertCircle className="w-4 h-4" />
                <span>{activeDocument.extraction_warnings.length} extraction warnings flagged</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Clean extraction · zero structural anomalies</span>
              </div>
            )}

            {duplicates.length > 0 && (
              <button
                onClick={() => setShowDuplicatesModal(true)}
                className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 underline font-medium"
              >
                <Copy className="w-3.5 h-3.5" />
                <span>{duplicates.length} duplicate questions detected</span>
              </button>
            )}
          </div>

          <div className="text-slate-400 text-[11px]">
            Original text is always immutably archived alongside edits.
          </div>
        </div>
      )}

      {/* Questions Workspace List */}
      {activeDocument && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-200">Extracted Question Workspace</h3>
              <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-mono">
                {questions.length} items
              </span>
            </div>
            <div className="text-xs text-slate-400">
              Preserving original order and syllabus taxonomy
            </div>
          </div>

          {loadingQuestions ? (
            <div className="p-8 text-center text-xs text-slate-400">Loading extracted questions...</div>
          ) : questions.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No questions found in this document. Try re-extracting or uploading another file.
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {questions.map((q) => {
                const showOriginal = !!showOriginalMap[q.id];
                return (
                  <div key={q.id} className="p-4 hover:bg-slate-800/30 transition-colors">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <span className="font-mono text-xs font-semibold text-slate-400 mt-0.5 w-6 shrink-0">
                          #{q.position}
                        </span>

                        <div className="space-y-2 flex-1">
                          <p className="text-sm text-slate-200 leading-relaxed font-medium">
                            {showOriginal && q.original_text ? q.original_text : q.question_text}
                          </p>

                          {/* Metadata chips */}
                          <div className="flex flex-wrap items-center gap-2 text-[11px]">
                            {q.marks !== null && q.marks !== undefined && (
                              <span className="bg-blue-950/70 text-blue-300 border border-blue-800/60 px-2 py-0.5 rounded font-mono font-medium">
                                {q.marks} Marks
                              </span>
                            )}
                            {q.bl && (
                              <span className="bg-purple-950/70 text-purple-300 border border-purple-800/60 px-2 py-0.5 rounded font-mono">
                                {q.bl}
                              </span>
                            )}
                            {q.co && (
                              <span className="bg-indigo-950/70 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded font-mono">
                                {q.co}
                              </span>
                            )}
                            {q.section && (
                              <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                                Section: {q.section}
                              </span>
                            )}
                            {q.source_page_start && (
                              <span className="text-slate-500">
                                Page {q.source_page_start}
                                {q.source_page_end && q.source_page_end !== q.source_page_start
                                  ? `–${q.source_page_end}`
                                  : ""}
                              </span>
                            )}
                            {q.extraction_confidence !== null && q.extraction_confidence !== undefined && (
                              <span className="text-slate-500">
                                Confidence: {Math.round(q.extraction_confidence * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Controls */}
                      <div className="flex items-center gap-1 shrink-0">
                        {q.original_text && q.original_text !== q.question_text && (
                          <button
                            onClick={() =>
                              setShowOriginalMap((prev) => ({ ...prev, [q.id]: !prev[q.id] }))
                            }
                            title="Toggle original extracted vs edited text"
                            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-amber-400 transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => openEditModal(q)}
                          title="Edit question text / metadata"
                          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-blue-400 transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedQuestionId(q.id);
                            setActiveTab("answer-studio");
                          }}
                          title="Open in Answer Studio"
                          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400 transition-colors"
                        >
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Edit Question Modal */}
      {editingQuestion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-slate-100 mb-1">
              Edit Question #{editingQuestion.position}
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Your edits are saved as current question text while the original extracted text remains preserved.
            </p>

            <form onSubmit={handleSaveQuestionEdit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Question Text</label>
                <textarea
                  rows={4}
                  required
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Marks</label>
                  <input
                    type="number"
                    min="1"
                    placeholder="e.g. 10"
                    value={editMarks}
                    onChange={(e) => setEditMarks(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Bloom's Level</label>
                  <input
                    type="text"
                    placeholder="e.g. BL3"
                    value={editBL}
                    onChange={(e) => setEditBL(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Course Outcome</label>
                  <input
                    type="text"
                    placeholder="e.g. CO2"
                    value={editCO}
                    onChange={(e) => setEditCO(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingQuestion(null)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Duplicate Questions Modal */}
      {showDuplicatesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-semibold text-slate-100">Duplicate Question Suggestions</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Answerly identifies semantically similar or repeated questions without deleting them.
                </p>
              </div>
              <button
                onClick={() => setShowDuplicatesModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-medium"
              >
                Close
              </button>
            </div>

            <div className="overflow-y-auto py-4 space-y-4">
              {duplicates.map((d, idx) => (
                <div key={idx} className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-medium text-amber-400">Match Reason: {d.reason}</span>
                    <span className="font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      Similarity: {Math.round(d.similarity * 100)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
                    <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800 text-slate-300">
                      <div className="text-[10px] text-slate-500 uppercase font-mono mb-1">Question A</div>
                      {d.text_1}
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800 text-slate-300">
                      <div className="text-[10px] text-slate-500 uppercase font-mono mb-1">Question B</div>
                      {d.text_2}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
