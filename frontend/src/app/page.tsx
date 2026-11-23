"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Header } from "../components/layout/Header";
import { WorkspaceNav } from "../components/layout/WorkspaceNav";
import { DocumentsTab } from "../components/documents/DocumentsTab";
import { ReferencesTab } from "../components/references/ReferencesTab";
import { ProcessingTab } from "../components/processing/ProcessingTab";
import { AnswerStudioTab } from "../components/answer-studio/AnswerStudioTab";
import { ExportsTab } from "../components/exports/ExportsTab";
import { AuthModal } from "../components/auth/AuthModal";
import { Sparkles, Shield, User, ArrowRight } from "lucide-react";

export default function Home() {
  const { isAuthenticated, activeTab, activeProject } = useApp();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Header onOpenAuth={() => setIsAuthModalOpen(true)} />

      {/* Guest Mode Indicator Banner */}
      {!isAuthenticated && (
        <div className="bg-gradient-to-r from-blue-950/60 via-indigo-950/40 to-slate-950 border-b border-blue-900/30 px-4 py-2">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 text-blue-300">
              <Sparkles className="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span>
                <strong>Interactive Demo Sandbox:</strong> You are exploring <em>{activeProject?.name}</em>. Full extraction, verifier audit & exports are active!
              </span>
            </div>
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="flex items-center gap-1.5 text-white bg-blue-600 hover:bg-blue-500 font-medium px-3 py-1 rounded-md transition-colors shrink-0"
            >
              <User className="w-3 h-3" />
              <span>Save to Personal Account</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}

      {/* Main 5-Stage Workspace Navigation */}
      <WorkspaceNav />

      {/* Active Workspace View */}
      <main className="flex-1 pb-16">
        {activeTab === "documents" && <DocumentsTab />}
        {activeTab === "references" && <ReferencesTab />}
        {activeTab === "processing" && <ProcessingTab />}
        {activeTab === "answer-studio" && <AnswerStudioTab />}
        {activeTab === "exports" && <ExportsTab />}
      </main>

      {/* Refined Academic Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/80 backdrop-blur-md py-5 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-300">Answerly</span>
            <span>· Exam Preparation & Question Workspace Engine</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono">
            <span>FastAPI Monolith</span>
            <span>•</span>
            <span>7-Criteria Verifier Pass</span>
            <span>•</span>
            <span>PyMuPDF & Tesseract OCR</span>
          </div>
        </div>
      </footer>

      <AuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />
    </div>
  );
}
