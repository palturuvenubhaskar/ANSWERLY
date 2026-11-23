"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Project, DocumentItem } from "../types";
import { api } from "../lib/api";
import { DEMO_PROJECT, DEMO_DOCUMENT } from "../lib/demoData";

export type WorkspaceTab = "documents" | "references" | "processing" | "answer-studio" | "exports";

export interface ToastMessage {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

interface AppContextType {
  token: string | null;
  isAuthenticated: boolean;
  projects: Project[];
  activeProject: Project | null;
  activeDocument: DocumentItem | null;
  activeTab: WorkspaceTab;
  selectedQuestionId: string | null;
  isBackendReady: boolean;
  toasts: ToastMessage[];
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  setActiveProject: (project: Project | null) => void;
  setActiveDocument: (doc: DocumentItem | null) => void;
  setActiveTab: (tab: WorkspaceTab) => void;
  setSelectedQuestionId: (qId: string | null) => void;
  refreshProjects: () => Promise<void>;
  notify: (message: string, type?: "success" | "error" | "info") => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([DEMO_PROJECT]);
  const [activeProject, setActiveProject] = useState<Project | null>(DEMO_PROJECT);
  const [activeDocument, setActiveDocument] = useState<DocumentItem | null>(DEMO_DOCUMENT);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("documents");
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>("demo-q1");
  const [isBackendReady, setIsBackendReady] = useState<boolean>(true);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const notify = (message: string, type: "success" | "error" | "info" = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const refreshProjects = async () => {
    try {
      const list = await api.listProjects();
      setProjects(list);
      if (list.length > 0 && (!activeProject || activeProject.id === DEMO_PROJECT.id)) {
        setActiveProject(list[0]);
      }
    } catch {
      // fallback to demo project
    }
  };

  useEffect(() => {
    const saved = localStorage.getItem("answerly_token");
    if (saved) {
      setTokenState(saved);
    }

    // Health check
    api.checkReady()
      .then(() => setIsBackendReady(true))
      .catch(() => setIsBackendReady(false));

    const interval = setInterval(() => {
      api.checkReady()
        .then(() => setIsBackendReady(true))
        .catch(() => setIsBackendReady(false));
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (token) {
      refreshProjects();
    }
  }, [token]);

  const login = async (email: string, pass: string) => {
    const res = await api.login(email, pass);
    setTokenState(res.access_token);
    notify("Signed in successfully", "success");
  };

  const register = async (email: string, pass: string) => {
    const res = await api.register(email, pass);
    setTokenState(res.access_token);
    notify("Account created and signed in", "success");
  };

  const logout = () => {
    api.logout();
    setTokenState(null);
    setActiveProject(DEMO_PROJECT);
    setActiveDocument(DEMO_DOCUMENT);
    notify("Signed out. Switched to demo workspace.", "info");
  };

  return (
    <AppContext.Provider
      value={{
        token,
        isAuthenticated: !!token,
        projects,
        activeProject,
        activeDocument,
        activeTab,
        selectedQuestionId,
        isBackendReady,
        toasts,
        login,
        register,
        logout,
        setActiveProject,
        setActiveDocument,
        setActiveTab,
        setSelectedQuestionId,
        refreshProjects,
        notify,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
