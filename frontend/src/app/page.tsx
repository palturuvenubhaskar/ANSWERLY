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
        <div className="answerly-demo-banner px-4 py-2.5">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-blue-300">
              <Sparkles className="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span className="leading-relaxed">
                <strong className="font-semibold">Sample workspace</strong>
                <span className="mx-1.5 opacity-50">/</span>
                Explore <em>{activeProject?.name}</em>. Create an account to keep your own projects and work.
              </span>
            </div>
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="answerly-demo-button flex items-center gap-1.5 font-medium px-3.5 py-2 transition-colors shrink-0"
            >
              <User className="w-3 h-3" />
              <span>Create account</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}

      {/* Main 5-Stage Workspace Navigation */}
      <WorkspaceNav />

      {/* Active Workspace View */}
      <main className="answerly-main flex-1 pb-16">
        {activeTab === "documents" && <DocumentsTab />}
        {activeTab === "references" && <ReferencesTab />}
        {activeTab === "processing" && <ProcessingTab />}
        {activeTab === "answer-studio" && <AnswerStudioTab />}
        {activeTab === "exports" && <ExportsTab />}
      </main>

      {/* Refined Academic Footer */}
      <footer className="answerly-footer py-5 text-xs">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <strong className="font-semibold">Answerly</strong>
            <span>For thoughtful exam preparation</span>
          </div>
          <span className="text-center">Review answer drafts before relying on them.</span>
        </div>
      </footer>

      <AuthModal isOpen={isAuthModalOpen} onClose={() => setIsAuthModalOpen(false)} />
    </div>
  );
}
