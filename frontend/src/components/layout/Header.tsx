"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { api } from "../../lib/api";
import {
  BookOpen,
  FolderPlus,
  ChevronDown,
  LogOut,
  LogIn,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Trash2,
} from "lucide-react";

interface HeaderProps {
  onOpenAuth: () => void;
}

export function Header({ onOpenAuth }: HeaderProps) {
  const {
    isAuthenticated,
    projects,
    activeProject,
    setActiveProject,
    refreshProjects,
    isBackendReady,
    logout,
    notify,
  } = useApp();

  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      notify("Please provide a project name", "error");
      return;
    }
    setCreating(true);
    try {
      const created = await api.createProject(newProjectName.trim(), newProjectDesc.trim() || undefined);
      await refreshProjects();
      setActiveProject(created);
      setIsNewProjectModalOpen(false);
      setNewProjectName("");
      setNewProjectDesc("");
      notify(`Project "${created.name}" created`, "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create project";
      notify(msg, "error");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteActiveProject = async () => {
    if (!activeProject) return;
    if (!window.confirm(`Are you sure you want to permanently delete "${activeProject.name}"?`)) return;
    try {
      await api.deleteProject(activeProject.id);
      notify(`Project deleted`, "info");
      await refreshProjects();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete project";
      notify(msg, "error");
    }
  };

  return (
    <>
      <header className="answerly-header sticky top-0 z-40">
        <div className="answerly-header-inner mx-auto flex items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div className="flex items-center gap-2.5">
            <div className="answerly-mark">
              <BookOpen className="w-4 h-4" strokeWidth={2} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="answerly-brand font-semibold tracking-tight text-base">Answerly</span>
                <span className="hidden lg:inline text-[11px] text-slate-500">
                  Study workspace
                </span>
              </div>
            </div>
          </div>

          {/* Project Switcher */}
          <div className="relative">
            <div className="answerly-project-switch flex items-center gap-1 p-1">
              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center gap-2 px-3 py-1 text-xs text-slate-200 hover:text-white transition-colors"
              >
                <span className="max-w-[220px] truncate font-medium">
                  {activeProject ? activeProject.name : "Select a Project"}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              </button>

              <button
                type="button"
                onClick={() => {
                  if (!isAuthenticated) {
                    onOpenAuth();
                  } else {
                    setIsNewProjectModalOpen(true);
                  }
                }}
                title="Create new project"
                className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-blue-400 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

              {isDropdownOpen && (
                <div className="answerly-project-menu absolute left-0 mt-2 w-64 bg-slate-900 border border-slate-800 rounded-lg shadow-2xl py-1 z-50">
                  <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800/80">
                    Your Projects
                  </div>
                  <div className="max-h-60 overflow-y-auto py-1">
                    {projects.length === 0 ? (
                      <div className="px-3 py-2 text-xs text-slate-500">No projects yet</div>
                    ) : (
                      projects.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => {
                            setActiveProject(p);
                            setIsDropdownOpen(false);
                          }}
                          className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-800/70 transition-colors ${
                            activeProject?.id === p.id ? "text-blue-400 font-medium bg-blue-950/30" : "text-slate-300"
                          }`}
                        >
                          <span className="truncate">{p.name}</span>
                          {activeProject?.id === p.id && <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />}
                        </button>
                      ))
                    )}
                  </div>
                  <div className="border-t border-slate-800/80 p-1 flex items-center justify-between">
                    <button
                      onClick={() => {
                        setIsDropdownOpen(false);
                        setIsNewProjectModalOpen(true);
                      }}
                      className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 px-2 py-1.5 w-full rounded hover:bg-slate-800/50"
                    >
                      <FolderPlus className="w-3.5 h-3.5" />
                      <span>New Project</span>
                    </button>
                    {activeProject && (
                      <button
                        onClick={() => {
                          setIsDropdownOpen(false);
                          handleDeleteActiveProject();
                        }}
                        title="Delete current project"
                        className="text-xs text-rose-400 hover:text-rose-300 p-1.5 rounded hover:bg-rose-950/40"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

          {/* Right side controls: Health indicator + User */}
          <div className="answerly-header-actions flex items-center gap-3">
            {/* Health pill */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                isBackendReady
                  ? "bg-emerald-950/60 border-emerald-800/50 text-emerald-300"
                  : "bg-amber-950/60 border-amber-800/50 text-amber-300"
              }`}
            >
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  isBackendReady ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                }`}
              />
              <span className="hidden lg:inline text-[11px]">{isBackendReady ? "Ready" : "Connecting..."}</span>
            </div>

            {/* Auth button */}
            {isAuthenticated ? (
              <button
                onClick={logout}
                aria-label="Sign out"
                title="Sign out"
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden lg:inline">Sign Out</span>
              </button>
            ) : (
              <button
                onClick={onOpenAuth}
                aria-label="Sign in"
                className="flex items-center gap-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-500 px-3.5 py-1.5 rounded-lg transition-colors shadow-sm"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span className="hidden lg:inline">Sign In</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* New Project Modal */}
      {isNewProjectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl">
            <h3 className="text-base font-semibold text-slate-100 mb-1">Create New Question Project</h3>
            <p className="text-xs text-slate-400 mb-4">
              A project groups your question-bank documents, reference notes, and exam answer drafts.
            </p>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., CS401 Distributed Systems Midterm"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Description <span className="text-slate-500 font-normal">(optional)</span>
                </label>
                <textarea
                  rows={2}
                  placeholder="Unit 1 to 5 past questions and syllabus outcomes"
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsNewProjectModalOpen(false)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                >
                  {creating ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
