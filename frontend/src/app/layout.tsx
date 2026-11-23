import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "../context/AppContext";
import { ToastContainer } from "../components/common/ToastContainer";

export const metadata: Metadata = {
  title: "Answerly — Exam-Oriented Answers from Question Banks",
  description:
    "Turn syllabus question banks into organized, verified, exam-oriented answers with transparent 7-criteria audits and multi-format exports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100 font-sans">
        <AppProvider>
          {children}
          <ToastContainer />
        </AppProvider>
      </body>
    </html>
  );
}
