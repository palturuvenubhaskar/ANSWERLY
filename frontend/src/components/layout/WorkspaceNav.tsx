"use client";

import React from "react";
import { useApp, WorkspaceTab } from "../../context/AppContext";
import {
  FileText,
  BookMarked,
  Cpu,
  GraduationCap,
  Download,
} from "lucide-react";

interface NavItem {
  id: WorkspaceTab;
  label: string;
  icon: React.ElementType;
  description: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "documents",
    label: "Documents & Extraction",
    icon: FileText,
    description: "Upload PDFs/DOCXs, review extracted questions & duplicates",
  },
  {
    id: "references",
    label: "Reference Excerpts",
    icon: BookMarked,
    description: "Attach textbook notes for source-consistency checking",
  },
  {
    id: "processing",
    label: "Processing Engine",
    icon: Cpu,
    description: "Parallel generation, verification, and live SSE progress",
  },
  {
    id: "answer-studio",
    label: "Answer Studio",
    icon: GraduationCap,
    description: "Inspect 7-criteria verification, edit drafts & approve",
  },
  {
    id: "exports",
    label: "Export Center",
    icon: Download,
    description: "Export exam answers to PDF, DOCX, Markdown, or JSON",
  },
];

export function WorkspaceNav() {
  const { activeTab, setActiveTab } = useApp();

  return (
    <nav className="border-b border-slate-800 bg-slate-950/40">
      <div className="max-w-7xl mx-auto px-4 flex items-center overflow-x-auto no-scrollbar">
        {NAV_ITEMS.map((item, index) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-2.5 px-4 py-3.5 border-b-2 text-xs font-medium whitespace-nowrap transition-colors ${
                isActive
                  ? "border-blue-500 text-blue-400 bg-blue-500/5 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              <div
                className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-mono ${
                  isActive ? "bg-blue-600/20 text-blue-400" : "bg-slate-800/80 text-slate-500"
                }`}
              >
                0{index + 1}
              </div>
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
