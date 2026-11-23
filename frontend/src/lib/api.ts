import {
  AuthResponse,
  Project,
  DocumentItem,
  QuestionItem,
  ReferenceExcerptItem,
  AnswerContent,
  LatestAnswerResponse,
  AnswerVersionItem,
  HumanDecisionRecord,
  ProcessingRunResponse,
  ProcessingJobItem,
  DocumentProgressResponse,
  DuplicateItem,
  ExportResponse,
} from "../types";
import {
  DEMO_PROJECT,
  DEMO_DOCUMENT,
  DEMO_QUESTIONS,
  DEMO_REFERENCES,
  DEMO_ANSWER_MAP,
  DEMO_PROGRESS,
} from "./demoData";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("answerly_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem("answerly_token", token);
  } else {
    localStorage.removeItem("answerly_token");
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail =
          typeof errJson.detail === "string"
            ? errJson.detail
            : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // System Health
  async checkHealth(): Promise<{ status: string }> {
    return request<{ status: string }>("/health");
  },

  async checkReady(): Promise<{ status: string }> {
    return request<{ status: string }>("/ready");
  },

  // Auth
  async register(email: string, password: string): Promise<AuthResponse> {
    const data = await request<AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const data = await request<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
  },

  logout() {
    setToken(null);
  },

  isAuthenticated(): boolean {
    return !!getToken();
  },

  // Projects
  async listProjects(): Promise<Project[]> {
    if (!getToken()) {
      return [DEMO_PROJECT];
    }
    try {
      const real = await request<Project[]>("/api/v1/projects");
      return real.length > 0 ? real : [DEMO_PROJECT];
    } catch {
      return [DEMO_PROJECT];
    }
  },

  async getProject(projectId: string): Promise<Project> {
    if (projectId === DEMO_PROJECT.id) {
      return DEMO_PROJECT;
    }
    return request<Project>(`/api/v1/projects/${projectId}`);
  },

  async createProject(name: string, description?: string): Promise<Project> {
    return request<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  },

  async updateProject(
    projectId: string,
    name?: string,
    description?: string
  ): Promise<Project> {
    if (projectId === DEMO_PROJECT.id) {
      return { ...DEMO_PROJECT, name: name || DEMO_PROJECT.name, description: description || DEMO_PROJECT.description };
    }
    return request<Project>(`/api/v1/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ name, description }),
    });
  },

  async deleteProject(projectId: string): Promise<void> {
    if (projectId === DEMO_PROJECT.id) {
      return;
    }
    return request<void>(`/api/v1/projects/${projectId}`, {
      method: "DELETE",
      body: JSON.stringify({ confirm: true }),
    });
  },

  // Documents
  async uploadDocument(projectId: string, file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", file);
    return request<DocumentItem>(`/api/v1/projects/${projectId}/documents`, {
      method: "POST",
      body: formData,
    });
  },

  async getDocument(documentId: string): Promise<DocumentItem> {
    if (documentId === DEMO_DOCUMENT.id) {
      return DEMO_DOCUMENT;
    }
    return request<DocumentItem>(`/api/v1/documents/${documentId}`);
  },

  async extractDocument(documentId: string): Promise<{
    id: string;
    status: DocumentItem["status"];
    extraction_warnings: string[];
  }> {
    if (documentId === DEMO_DOCUMENT.id) {
      return { id: DEMO_DOCUMENT.id, status: "READY", extraction_warnings: [] };
    }
    return request(`/api/v1/documents/${documentId}/extract`, {
      method: "POST",
    });
  },

  async listDocumentQuestions(documentId: string): Promise<QuestionItem[]> {
    if (documentId === DEMO_DOCUMENT.id) {
      return DEMO_QUESTIONS;
    }
    return request<QuestionItem[]>(`/api/v1/documents/${documentId}/questions`);
  },

  async confirmExtraction(
    documentId: string
  ): Promise<{ id: string; status: DocumentItem["status"] }> {
    if (documentId === DEMO_DOCUMENT.id) {
      return { id: DEMO_DOCUMENT.id, status: "READY" };
    }
    return request(`/api/v1/documents/${documentId}/confirm-extraction`, {
      method: "POST",
    });
  },

  async getDocumentDuplicates(documentId: string): Promise<DuplicateItem[]> {
    if (documentId === DEMO_DOCUMENT.id) {
      return [
        {
          question_id_1: "demo-q1",
          question_id_2: "demo-q3",
          text_1: DEMO_QUESTIONS[0].question_text,
          text_2: "Compare Paxos consensus with Vector Clocks for causal ordering",
          similarity: 0.68,
          reason: "Semantic overlap on distributed consensus & coordination mechanisms",
        },
      ];
    }
    return request<DuplicateItem[]>(`/api/v1/documents/${documentId}/duplicates`);
  },

  // Reference Excerpts
  async listReferences(projectId: string): Promise<ReferenceExcerptItem[]> {
    if (projectId === DEMO_PROJECT.id) {
      return DEMO_REFERENCES;
    }
    return request<ReferenceExcerptItem[]>(`/api/v1/projects/${projectId}/references`);
  },

  async createReference(
    projectId: string,
    data: { title: string; text: string; source_label: string; page?: number | null }
  ): Promise<ReferenceExcerptItem> {
    if (projectId === DEMO_PROJECT.id) {
      return {
        id: `ref-${Date.now()}`,
        ...data,
      };
    }
    return request<ReferenceExcerptItem>(`/api/v1/projects/${projectId}/references`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async deleteReference(referenceId: string): Promise<void> {
    if (referenceId.startsWith("ref-")) {
      return;
    }
    return request<void>(`/api/v1/references/${referenceId}`, {
      method: "DELETE",
    });
  },

  // Questions CRUD
  async getQuestion(questionId: string): Promise<QuestionItem> {
    const demo = DEMO_QUESTIONS.find((q) => q.id === questionId);
    if (demo) return demo;
    return request<QuestionItem>(`/api/v1/questions/${questionId}`);
  },

  async createQuestion(
    projectId: string,
    questionText: string,
    marks?: number | null
  ): Promise<QuestionItem> {
    return request<QuestionItem>(`/api/v1/projects/${projectId}/questions`, {
      method: "POST",
      body: JSON.stringify({ question_text: questionText, marks }),
    });
  },

  async updateQuestion(
    questionId: string,
    data: {
      question_text?: string;
      marks?: number | null;
      bl?: string | null;
      co?: string | null;
      position?: number | null;
    }
  ): Promise<QuestionItem> {
    const demo = DEMO_QUESTIONS.find((q) => q.id === questionId);
    if (demo) {
      return {
        ...demo,
        ...data,
        position: data.position !== null && data.position !== undefined ? data.position : demo.position,
      };
    }
    return request<QuestionItem>(`/api/v1/questions/${questionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteQuestion(questionId: string): Promise<void> {
    return request<void>(`/api/v1/questions/${questionId}`, {
      method: "DELETE",
    });
  },

  async reorderQuestions(
    documentId: string,
    orderedQuestionIds: string[]
  ): Promise<{ status: string; count: number }> {
    return request(`/api/v1/documents/${documentId}/questions/reorder`, {
      method: "POST",
      body: JSON.stringify({ ordered_question_ids: orderedQuestionIds }),
    });
  },

  // Processing & Jobs
  async startProcessing(
    documentId: string,
    idempotencyKey: string,
    questionIds: string[] = [],
    referenceIds: string[] = []
  ): Promise<ProcessingRunResponse> {
    if (documentId === DEMO_DOCUMENT.id) {
      return {
        id: `run-${Date.now()}`,
        project_id: DEMO_PROJECT.id,
        idempotency_key: idempotencyKey,
        jobs: questionIds.map((qId) => ({
          id: `job-${qId}`,
          question_id: qId,
          status: "VERIFIER_APPROVED",
          revision_count: 0,
          retry_count: 0,
        })),
      };
    }
    return request<ProcessingRunResponse>(
      `/api/v1/documents/${documentId}/process`,
      {
        method: "POST",
        headers: {
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({
          question_ids: questionIds,
          reference_ids: referenceIds,
        }),
      }
    );
  },

  async getJob(jobId: string): Promise<ProcessingJobItem> {
    return request<ProcessingJobItem>(`/api/v1/jobs/${jobId}`);
  },

  async cancelJob(jobId: string): Promise<{ id: string; status: string; cancel_requested: boolean }> {
    return request(`/api/v1/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  },

  async executeJob(jobId: string): Promise<{ id: string; status: string; revision_count: number; finished_at: string | null }> {
    if (jobId.startsWith("job-demo")) {
      return { id: jobId, status: "VERIFIER_APPROVED", revision_count: 0, finished_at: new Date().toISOString() };
    }
    return request(`/api/v1/jobs/${jobId}/execute`, {
      method: "POST",
    });
  },

  async regenerateQuestion(
    questionId: string,
    idempotencyKey?: string
  ): Promise<{ run_id: string; job_id: string; status: string }> {
    if (questionId.startsWith("demo-")) {
      return { run_id: `run-${Date.now()}`, job_id: `job-${questionId}`, status: "VERIFIER_APPROVED" };
    }
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }
    return request(`/api/v1/questions/${questionId}/regenerate`, {
      method: "POST",
      headers,
    });
  },

  // Progress & Events
  async getDocumentProgress(documentId: string): Promise<DocumentProgressResponse> {
    if (documentId === DEMO_DOCUMENT.id) {
      return DEMO_PROGRESS;
    }
    return request<DocumentProgressResponse>(`/api/v1/documents/${documentId}/progress`);
  },

  listenToDocumentEvents(
    documentId: string,
    onProgress: (data: DocumentProgressResponse) => void,
    onError?: (err: unknown) => void
  ): () => void {
    if (documentId === DEMO_DOCUMENT.id) {
      onProgress(DEMO_PROGRESS);
      return () => {};
    }

    const token = getToken();
    // SSE does not support Authorization headers; pass token as query param
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
    const url = `${API_BASE}/api/v1/documents/${documentId}/events${tokenParam}`;
    
    let eventSource: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;

    try {
      eventSource = new EventSource(url);
      
      eventSource.addEventListener("progress", (evt) => {
        try {
          const parsed = JSON.parse(evt.data);
          onProgress(parsed);
        } catch {
          // ignore
        }
      });

      eventSource.onerror = () => {
        if (!pollInterval) {
          pollInterval = setInterval(async () => {
            try {
              const res = await api.getDocumentProgress(documentId);
              onProgress(res);
            } catch (err) {
              if (onError) onError(err);
            }
          }, 2500);
        }
      };
    } catch {
      pollInterval = setInterval(async () => {
        try {
          const res = await api.getDocumentProgress(documentId);
          onProgress(res);
        } catch (err) {
          if (onError) onError(err);
        }
      }, 2500);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  },

  // Answers & Decisions
  async getLatestAnswer(questionId: string): Promise<LatestAnswerResponse> {
    if (DEMO_ANSWER_MAP[questionId]) {
      return DEMO_ANSWER_MAP[questionId];
    }
    if (questionId === "demo-q2") {
      return {
        question_id: "demo-q2",
        answer_version_id: "ans-ver-cap-v1",
        version_number: 1,
        provider: "OpenRouter",
        model: "claude-3-5-sonnet",
        created_at: new Date().toISOString(),
        latest_human_decision: "APPROVED",
        answer: {
          introduction:
            "Formulated by Eric Brewer in 2000 and proven by Seth Gilbert and Nancy Lynch in 2002, the CAP theorem establishes that any distributed data store can simultaneously provide at most two out of three guarantees: Consistency, Availability, and Partition Tolerance.",
          sections: [
            {
              heading: "The Three Guarantees Formulated",
              content:
                "Consistency (C) mandates linearizability—every read must receive the most recent write or an error. Availability (A) requires that every non-failing node must return a non-error response. Partition Tolerance (P) guarantees the system continues to operate despite arbitrary dropped or delayed messages.",
              bullets: [
                "Consistency (C): Linearizable single-copy semantics across all nodes.",
                "Availability (A): 100% success rate on non-failing node read/write operations.",
                "Partition Tolerance (P): Non-negotiable physical reality of distributed networks.",
              ],
              formula: "P is unavoidable in real networks ⇒ The fundamental choice is CP vs AP",
              example: null,
            },
            {
              heading: "Real-World Comparison: DynamoDB (AP) vs Google Spanner (CP)",
              content:
                "Under network partition, DynamoDB chooses Availability (returning stale data and resolving conflicts with vector clocks or last-write-wins), whereas Google Spanner chooses Consistency (holding locks and halting reads until true quorum commits via atomic clocks).",
              bullets: [
                "DynamoDB (AP): Prioritizes high write-throughput and uninterrupted shopping cart availability.",
                "Google Spanner (CP): Synchronizes globally using TrueTime GPS/Atomic hardware to guarantee external consistency at the expense of latency.",
              ],
              formula: null,
              example: "During an undersea cable cut between US-East and EU-West, DynamoDB accepts conflicting regional writes; Spanner pauses transactions across disconnected replicas.",
            },
          ],
          conclusion:
            "Because physical network delays and partitions are inevitable, distributed system architects do not choose between CA, CP, and AP in the abstract; rather, they trade consistency for availability during partitions.",
        },
        verifier_report: {
          verdict: "approved",
          confidence: 0.96,
          criteria: [
            { name: "accuracy", status: "pass", notes: "Precise Gilbert-Lynch definition of linearizability." },
            { name: "coverage", status: "pass", notes: "Covers all three properties, trade-off proof, and DynamoDB/Spanner contrast." },
            { name: "marks_suitability", status: "pass", notes: "Detailed analysis appropriate for 10 marks." },
            { name: "clarity", status: "pass", notes: "Logical section division with clear comparison points." },
            { name: "technical_details", status: "pass", notes: "Correct TrueTime hardware mechanism cited for Spanner." },
            { name: "source_consistency", status: "pass", notes: "Consistent with Kleppmann reference excerpt on p. 324." },
            { name: "citations", status: "pass", notes: "Properly credits Brewer (2000) and Gilbert/Lynch (2002)." },
          ],
          issues: [],
          evidence_notes: ["Verified against Martin Kleppmann: Designing Data-Intensive Applications, p. 324."],
        },
      };
    }
    return request<LatestAnswerResponse>(`/api/v1/questions/${questionId}/answer`);
  },

  async getAnswerVersions(questionId: string): Promise<AnswerVersionItem[]> {
    if (DEMO_ANSWER_MAP[questionId]) {
      return [
        {
          id: "ans-ver-paxos-v1",
          version_number: 1,
          answer: DEMO_ANSWER_MAP[questionId].answer,
          provider: "OpenRouter",
          model: "claude-3-haiku",
          created_at: new Date(Date.now() - 7200000).toISOString(),
          verifier_report: null,
          human_approvals: [{ decision: "REJECTED", reviewer_id: "reviewer-1", created_at: new Date(Date.now() - 7000000).toISOString() }],
        },
        {
          id: "ans-ver-paxos-v2",
          version_number: 2,
          answer: DEMO_ANSWER_MAP[questionId].answer,
          provider: "OpenRouter",
          model: "claude-3-5-sonnet",
          created_at: new Date(Date.now() - 3600000).toISOString(),
          verifier_report: DEMO_ANSWER_MAP[questionId].verifier_report,
          human_approvals: [{ decision: "APPROVED", reviewer_id: "reviewer-1", created_at: new Date(Date.now() - 1800000).toISOString() }],
        },
      ];
    }
    return request<AnswerVersionItem[]>(`/api/v1/questions/${questionId}/versions`);
  },

  async saveAnswerEdit(questionId: string, answer: AnswerContent): Promise<{
    id: string;
    version_number: number;
    answer: AnswerContent;
    created_at: string;
  }> {
    if (questionId.startsWith("demo-")) {
      return {
        id: `ans-ver-user-${Date.now()}`,
        version_number: 3,
        answer,
        created_at: new Date().toISOString(),
      };
    }
    return request(`/api/v1/questions/${questionId}/answer`, {
      method: "PATCH",
      body: JSON.stringify({ answer }),
    });
  },

  async recordApproval(
    questionId: string,
    answerVersionId: string,
    decision: "APPROVED" | "REJECTED"
  ): Promise<HumanDecisionRecord> {
    if (questionId.startsWith("demo-")) {
      return {
        id: `decision-${Date.now()}`,
        answer_version_id: answerVersionId,
        decision,
        created_at: new Date().toISOString(),
      };
    }
    return request<HumanDecisionRecord>(`/api/v1/questions/${questionId}/approve`, {
      method: "POST",
      body: JSON.stringify({
        answer_version_id: answerVersionId,
        decision,
      }),
    });
  },

  async listApprovals(questionId: string): Promise<HumanDecisionRecord[]> {
    return request<HumanDecisionRecord[]>(`/api/v1/questions/${questionId}/approvals`);
  },

  // Exports
  async createExport(
    documentId: string,
    format: "pdf" | "docx" | "md" | "json",
    questionIds?: string[],
    includeUnapproved: boolean = false
  ): Promise<ExportResponse> {
    if (documentId === DEMO_DOCUMENT.id) {
      return {
        id: `exp-${format}-${Date.now().toString(36)}`,
        document_id: DEMO_DOCUMENT.id,
        format,
        status: "COMPLETED",
        file_size_bytes: format === "pdf" ? 142050 : format === "docx" ? 84200 : 12400,
        sha256: "9a2f1b8c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a",
        created_at: new Date().toISOString(),
      };
    }
    return request<ExportResponse>(`/api/v1/documents/${documentId}/exports`, {
      method: "POST",
      body: JSON.stringify({
        format,
        question_ids: questionIds && questionIds.length > 0 ? questionIds : null,
        include_unapproved: includeUnapproved,
      }),
    });
  },

  async getExport(exportId: string): Promise<ExportResponse> {
    return request<ExportResponse>(`/api/v1/exports/${exportId}`);
  },

  async downloadExport(exportId: string, filename: string): Promise<void> {
    if (exportId.startsWith("exp-")) {
      // Generate synthetic download file for demo
      const format = filename.split(".").pop() || "txt";
      let content = "";
      if (format === "json") {
        content = JSON.stringify(
          {
            project: DEMO_PROJECT.name,
            document: DEMO_DOCUMENT.title,
            questions: DEMO_QUESTIONS,
            sample_answers: DEMO_ANSWER_MAP,
          },
          null,
          2
        );
      } else if (format === "md") {
        content = `# ${DEMO_PROJECT.name}\n## Document: ${DEMO_DOCUMENT.title}\n\n### Q1. ${DEMO_QUESTIONS[0].question_text} [10 Marks]\n\n${DEMO_ANSWER_MAP["demo-q1"].answer.introduction}\n\n`;
      } else {
        content = `Answerly Exam Booklet - ${DEMO_PROJECT.name}\nDocument: ${DEMO_DOCUMENT.title}\nExport ID: ${exportId}\n`;
      }
      const blob = new Blob([content], { type: "text/plain" });
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      a.remove();
      return;
    }

    const token = getToken();
    const url = `${API_BASE}/api/v1/exports/${exportId}/download`;
    const res = await fetch(url, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!res.ok) {
      throw new Error(`Failed to download export (${res.statusText})`);
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    a.remove();
  },
};
