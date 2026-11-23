"use client";

import React from "react";
import { useApp } from "../../context/AppContext";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";

export function ToastContainer() {
  const { toasts } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start gap-3 p-3.5 rounded-lg border text-sm shadow-xl pointer-events-auto backdrop-blur-md transition-all duration-200 ${
            t.type === "success"
              ? "bg-emerald-950/90 border-emerald-800/80 text-emerald-200"
              : t.type === "error"
              ? "bg-rose-950/90 border-rose-800/80 text-rose-200"
              : "bg-slate-900/95 border-slate-700/80 text-slate-200"
          }`}
        >
          {t.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />}
          {t.type === "error" && <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />}
          {t.type === "info" && <Info className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />}
          <div className="flex-1 leading-snug">{t.message}</div>
        </div>
      ))}
    </div>
  );
}
