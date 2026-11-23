"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";
import { api } from "../../lib/api";
import { ReferenceExcerptItem } from "../../types";
import {
  BookMarked,
  Plus,
  Trash2,
  FileText,
  BookOpen,
  HelpCircle,
  ExternalLink,
} from "lucide-react";

export function ReferencesTab() {
  const { activeProject, notify } = useApp();
  const [references, setReferences] = useState<ReferenceExcerptItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Form state
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [sourceLabel, setSourceLabel] = useState("");
  const [page, setPage] = useState<string>("");
  const [saving, setSaving] = useState(false);

  const loadReferences = async () => {
    if (!activeProject) return;
    setLoading(true);
    try {
      const list = await api.listReferences(activeProject.id);
      setReferences(list);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load reference excerpts";
      notify(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReferences();
  }, [activeProject]);

  const handleAddExcerpt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject) return;
    if (!title.trim() || !text.trim() || !sourceLabel.trim()) {
      notify("Please fill in the title, source label, and text content", "error");
      return;
    }

    setSaving(true);
    try {
      const created = await api.createReference(activeProject.id, {
        title: title.trim(),
        text: text.trim(),
        source_label: sourceLabel.trim(),
        page: page.trim() ? parseInt(page.trim(), 10) : null,
      });
      setReferences((prev) => [...prev, created]);
      setIsAddModalOpen(false);
      setTitle("");
      setText("");
      setSourceLabel("");
      setPage("");
      notify("Reference excerpt added", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add reference excerpt";
      notify(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteExcerpt = async (id: string, excerptTitle: string) => {
    if (!window.confirm(`Delete reference excerpt "${excerptTitle}"?`)) return;
    try {
      await api.deleteReference(id);
      setReferences((prev) => prev.filter((r) => r.id !== id));
      notify("Reference excerpt removed", "info");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete excerpt";
      notify(msg, "error");
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500 mb-4">
          <BookMarked className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-semibold text-slate-200">No project selected</h2>
        <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
          Create or select a project from the top bar to manage reference excerpts.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <span>Textbook & Syllabus Reference Excerpts</span>
            <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-mono">
              {references.length}
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Supply trusted textbook passages, formula sheets, or syllabus notes. When processing questions, the
            independent verifier agent uses these excerpts to evaluate <strong>source consistency</strong> and{" "}
            <strong>accuracy</strong>.
          </p>
        </div>

        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs px-4 py-2.5 rounded-lg shadow-sm transition-colors whitespace-nowrap"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Reference Excerpt</span>
        </button>
      </div>

      {/* Excerpts Grid */}
      {loading ? (
        <div className="p-8 text-center text-xs text-slate-400">Loading reference excerpts...</div>
      ) : references.length === 0 ? (
        <div className="bg-slate-900/30 border border-dashed border-slate-800 rounded-xl p-12 text-center max-w-xl mx-auto">
          <div className="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center mx-auto text-slate-400 mb-3">
            <BookOpen className="w-5 h-5 text-blue-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">No reference excerpts yet</h3>
          <p className="text-xs text-slate-400 mt-1">
            Add key textbook chapters, theorem definitions, or professor lecture notes to anchor generated answers.
          </p>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="mt-4 inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 font-medium"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add your first excerpt</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {references.map((ref) => (
            <div
              key={ref.id}
              className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition-colors"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-semibold text-slate-200 leading-snug">{ref.title}</h4>
                  <button
                    onClick={() => handleDeleteExcerpt(ref.id, ref.title)}
                    title="Delete excerpt"
                    className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-2 text-xs text-blue-400 font-medium">
                  <span>{ref.source_label}</span>
                  {ref.page && <span className="text-slate-500 font-mono">• Page {ref.page}</span>}
                </div>

                <p className="text-xs text-slate-400 leading-relaxed line-clamp-4 bg-slate-950/60 p-2.5 rounded border border-slate-850 font-serif">
                  {ref.text}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
                <span>{ref.text.length} characters</span>
                <span className="font-mono">ID: {ref.id.substring(0, 8)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Reference Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-slate-100 mb-1">Add Reference Excerpt</h3>
            <p className="text-xs text-slate-400 mb-4">
              Enter excerpt text directly from your course textbook or verified study notes.
            </p>

            <form onSubmit={handleAddExcerpt} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Excerpt Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Paxos Consensus Protocol Specification"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Source / Textbook Label</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Tanenbaum: Dist. Systems 3e"
                    value={sourceLabel}
                    onChange={(e) => setSourceLabel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Page Number <span className="text-slate-500 font-normal">(optional)</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    placeholder="e.g. 142"
                    value={page}
                    onChange={(e) => setPage(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Excerpt Text Content</label>
                <textarea
                  rows={6}
                  required
                  placeholder="Paste textbook definitions, key algorithms, or authoritative explanations..."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-100 focus:outline-none focus:border-blue-500 resize-none font-serif leading-relaxed"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                >
                  {saving ? "Saving..." : "Add Excerpt"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
