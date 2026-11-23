import {
  Project,
  DocumentItem,
  QuestionItem,
  ReferenceExcerptItem,
  LatestAnswerResponse,
  AnswerVersionItem,
  DocumentProgressResponse,
} from "../types";

export const DEMO_PROJECT: Project = {
  id: "demo-project-cs401",
  name: "CS401 Distributed Systems & Cloud Computing",
  description: "Midterm question bank covering Units 1–3: Consensus, Clock Synchronization, and Fault Tolerance.",
  created_at: new Date().toISOString(),
  question_count: 4,
  reference_count: 2,
};

export const DEMO_DOCUMENT: DocumentItem = {
  id: "demo-doc-midterm",
  project_id: "demo-project-cs401",
  title: "CS401_Midterm_QuestionBank_2024.pdf",
  original_filename: "CS401_Midterm_QuestionBank_2024.pdf",
  file_size_bytes: 482104,
  mime_type: "application/pdf",
  sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  status: "READY",
  extraction_warnings: [],
};

export const DEMO_QUESTIONS: QuestionItem[] = [
  {
    id: "demo-q1",
    project_id: "demo-project-cs401",
    document_id: "demo-doc-midterm",
    position: 1,
    question_number: "Q1",
    section: "Part B — Consensus",
    question_text:
      "Explain the two phases of the Paxos consensus protocol (Prepare/Promise and Accept/Accepted) and prove how it guarantees safety in an asynchronous network with crash faults.",
    original_text:
      "Explain the two phases of the Paxos consensus protocol (Prepare/Promise and Accept/Accepted) and prove how it guarantees safety in an asynchronous network with crash faults.",
    marks: 10,
    bl: "BL4 Analyze",
    co: "CO3",
    source_page_start: 3,
    source_page_end: 4,
    extraction_confidence: 0.98,
    status: "VERIFIER_APPROVED",
  },
  {
    id: "demo-q2",
    project_id: "demo-project-cs401",
    document_id: "demo-doc-midterm",
    position: 2,
    question_number: "Q2",
    section: "Part B — Distributed Storage",
    question_text:
      "State the CAP Theorem. In the presence of a network partition, explain why a distributed data store must choose between Consistency and Availability. Provide a concrete example using DynamoDB vs Google Spanner.",
    original_text:
      "State the CAP Theorem. In the presence of a network partition, explain why a distributed data store must choose between Consistency and Availability. Provide a concrete example using DynamoDB vs Google Spanner.",
    marks: 10,
    bl: "BL3 Apply",
    co: "CO2",
    source_page_start: 5,
    source_page_end: 5,
    extraction_confidence: 0.96,
    status: "VERIFIER_APPROVED",
  },
  {
    id: "demo-q3",
    project_id: "demo-project-cs401",
    document_id: "demo-doc-midterm",
    position: 3,
    question_number: "Q3",
    section: "Part A — Logical Clocks",
    question_text:
      "Compare and contrast Vector Clocks with Lamport Timestamps. How does a vector clock detect causal concurrency violations?",
    original_text:
      "Compare and contrast Vector Clocks with Lamport Timestamps. How does a vector clock detect causal concurrency violations?",
    marks: 5,
    bl: "BL4 Analyze",
    co: "CO1",
    source_page_start: 2,
    source_page_end: 2,
    extraction_confidence: 0.99,
    status: "VERIFIER_APPROVED",
  },
  {
    id: "demo-q4",
    project_id: "demo-project-cs401",
    document_id: "demo-doc-midterm",
    position: 4,
    question_number: "Q4",
    section: "Part C — Distributed Compute",
    question_text:
      "Describe the MapReduce computational framework with a diagram showing the Map, Shuffle/Sort, and Reduce stages for word count.",
    original_text:
      "Describe the MapReduce computational framework with a diagram showing the Map, Shuffle/Sort, and Reduce stages for word count.",
    marks: 15,
    bl: "BL3 Apply",
    co: "CO3",
    source_page_start: 6,
    source_page_end: 8,
    extraction_confidence: 0.94,
    status: "MANUAL_REVIEW",
  },
];

export const DEMO_REFERENCES: ReferenceExcerptItem[] = [
  {
    id: "ref-1",
    title: "Paxos Protocol Invariants & Quorum Requirements",
    source_label: "Leslie Lamport: Paxos Made Simple (ACM SIGACT)",
    page: 51,
    text: "A consensus algorithm must ensure that a single value is chosen among proposed values. In Paxos, phase 1a sends prepare(n) with proposal number n. Phase 1b promises not to accept proposals numbered less than n and returns the highest-numbered proposal accepted so far. Phase 2a issues accept(n, v) to a majority quorum.",
  },
  {
    id: "ref-2",
    title: "CAP Theorem Formulation and Trade-offs",
    source_label: "Martin Kleppmann: Designing Data-Intensive Applications",
    page: 324,
    text: "The CAP theorem states that in a distributed data system with network partitions (P), you can choose either linearizable consistency (C) or total availability (A), but not both simultaneously across partitions.",
  },
];

export const DEMO_ANSWER_MAP: Record<string, LatestAnswerResponse> = {
  "demo-q1": {
    question_id: "demo-q1",
    answer_version_id: "ans-ver-paxos-v2",
    version_number: 2,
    provider: "OpenRouter",
    model: "claude-3-5-sonnet",
    created_at: new Date(Date.now() - 3600000).toISOString(),
    latest_human_decision: "APPROVED",
    answer: {
      introduction:
        "The Paxos protocol, formulated by Leslie Lamport, is the foundational distributed consensus algorithm that guarantees agreement on a single value across a collection of unreliable processes operating over an asynchronous, lossy network without Byzantine faults.",
      sections: [
        {
          heading: "Phase 1: Prepare & Promise (Acquiring Quorum Leadership)",
          content:
            "A Proposer selects a globally unique, monotonically increasing proposal number n and broadcasts a Prepare(n) request to a majority quorum of Acceptors. This phase acts as a distributed lock and discovery mechanism.",
          bullets: [
            "Proposer chooses proposal number n such that n > any previous proposal number it has used.",
            "Acceptors receive Prepare(n). If n > any proposal number previously promised, the Acceptor responds with a Promise(n).",
            "The Promise commits the Acceptor to reject any future proposals numbered less than n.",
            "Crucially, the Acceptor returns the proposal number and value (k, v) of the highest-numbered proposal it has already accepted, if any.",
          ],
          formula: "n = (round_number * N_nodes) + node_id  (guarantees uniqueness without coordination)",
          example:
            "If Acceptor A1 previously accepted (n=3, v='valA'), when responding to Prepare(n=5), it promises n=5 and reports (3, 'valA').",
        },
        {
          heading: "Phase 2: Accept & Accepted (Committing the Consensus Value)",
          content:
            "Once the Proposer gathers Promise responses from a majority quorum (at least ⌊N/2⌋ + 1 nodes), it selects the value v associated with the highest proposal number returned in the promises. If no Acceptor reported an earlier value, the Proposer is free to choose its own proposed value.",
          bullets: [
            "Proposer broadcasts Accept(n, v) to the majority quorum.",
            "An Acceptor accepts proposal (n, v) if and only if it has not promised to disregard proposal n (i.e., no Prepare(n' > n) was received).",
            "If accepted, the Acceptor sends an Accepted(n, v) confirmation to the Proposer and Learners.",
            "Consensus is reached when a majority of Acceptors accept the exact same value v.",
          ],
          formula: "Quorum Intersection: |Q_1 ∩ Q_2| ≥ 1  (Any two majority quorums share at least one node)",
          example:
            "With 5 nodes (A, B, C, D, E), any majority quorum requires 3 nodes. Any two quorums {A, B, C} and {C, D, E} overlap at node C.",
        },
        {
          heading: "Proof of Safety (Invariance Property)",
          content:
            "Paxos guarantees that if a value v has been chosen with proposal number n, then every proposal with number m > n chosen by any proposer must also propose value v.",
          bullets: [
            "Proof by Induction: Suppose proposal (n, v) is chosen by quorum Q1.",
            "For any subsequent proposal m > n to reach phase 2, its proposer must receive promises from a majority quorum Q2.",
            "By the pigeonhole principle, Q1 and Q2 must overlap at at least one node X ∈ Q1 ∩ Q2.",
            "Node X already accepted (n, v), so its promise to Q2 reveals (n, v).",
            "The proposer for m is strictly bound by rule to adopt v, preventing any conflicting value from ever being chosen.",
          ],
          formula: "Safety Condition: If chosen(n, v) and chosen(m, v') and m > n ⇒ v = v'",
          example: null,
        },
      ],
      conclusion:
        "Paxos guarantees non-blocking safety even under unbounded message delays and network partitions, provided a majority of nodes remain reachable. While liveness is subject to the FLP impossibility theorem (potential dueling proposers), randomized backoff resolves contention in practical implementations.",
      diagram_source:
        "sequenceDiagram\n  autonumber\n  Proposer->>Acceptors: Phase 1a: Prepare(n=5)\n  Acceptors-->>Proposer: Phase 1b: Promise(n=5, prev_val=null)\n  Proposer->>Acceptors: Phase 2a: Accept(n=5, v='Commit')\n  Acceptors-->>Learner: Phase 2b: Accepted(n=5, v='Commit')",
    },
    verifier_report: {
      verdict: "approved",
      confidence: 0.94,
      criteria: [
        {
          name: "accuracy",
          status: "pass",
          notes: "Fully accurate protocol definition with correct Phase 1a/1b and Phase 2a/2b invariants.",
        },
        {
          name: "coverage",
          status: "pass",
          notes: "Covers prepare, promise, accept, accepted, safety proof by quorum intersection, and fault model.",
        },
        {
          name: "marks_suitability",
          status: "pass",
          notes: "Comprehensive structure and depth thoroughly justify 10 exam marks.",
        },
        {
          name: "clarity",
          status: "pass",
          notes: "Exemplary student-friendly language with clean sub-headings and bullet points.",
        },
        {
          name: "technical_details",
          status: "pass",
          notes: "Unique proposal generation formula and quorum intersection logic mathematically sound.",
        },
        {
          name: "source_consistency",
          status: "pass",
          notes: "Strictly aligns with Lamport's 'Paxos Made Simple' reference excerpt on page 51.",
        },
        {
          name: "citations",
          status: "pass",
          notes: "Properly grounds safety proof and cites FLP theorem appropriately.",
        },
      ],
      issues: [],
      evidence_notes: [
        "Compared against Reference Excerpt #1 (Lamport: Paxos Made Simple, p. 51).",
        "Verified majority quorum intersection rule (N/2 + 1).",
      ],
    },
  },
};

export const DEMO_PROGRESS: DocumentProgressResponse = {
  document_id: "demo-doc-midterm",
  total: 4,
  completed: 4,
  percent: 100.0,
  counts: {
    PENDING: 0,
    QUEUED: 0,
    GENERATING: 0,
    VERIFYING: 0,
    REVISING: 0,
    VERIFIER_APPROVED: 3,
    MANUAL_REVIEW: 1,
    FAILED: 0,
    CANCELLED: 0,
  },
};
