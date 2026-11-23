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
    label: "Questions",
    icon: FileText,
    description: "Add a question bank and check its contents",
  },
  {
    id: "references",
    label: "References",
    icon: BookMarked,
    description: "Keep trusted course notes close at hand",
  },
  {
    id: "processing",
    label: "Prepare",
    icon: Cpu,
    description: "Draft answers and run verifier checks",
  },
  {
    id: "answer-studio",
    label: "Review",
    icon: GraduationCap,
    description: "Inspect checks, edit drafts, record decisions",
  },
  {
    id: "exports",
    label: "Export",
    icon: Download,
    description: "Download your answer set in a useful format",
  },
];

export function WorkspaceNav() {
  const { activeTab, setActiveTab } = useApp();

  return (
    <nav aria-label="Workspace stages" className="answerly-nav">
      <div className="answerly-nav-inner mx-auto flex items-center overflow-x-auto no-scrollbar">
        {NAV_ITEMS.map((item, index) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              aria-current={isActive ? "step" : undefined}
              className={`answerly-step flex items-center gap-2.5 px-4 text-xs font-medium whitespace-nowrap transition-colors ${
                isActive
                  ? "border-blue-500 text-blue-400 bg-blue-500/5 font-semibold"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              <div className="answerly-step-marker">
                {index + 1}
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
