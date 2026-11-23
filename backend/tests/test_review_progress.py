import io
import fitz
import pytest
from fastapi.testclient import TestClient


def create_sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    content = """UNIT 1: DATABASE
Q1. Explain ACID properties with examples. [10 Marks]
Q2. What is 2-Phase Locking protocol? (5 Marks)
"""
    page.insert_text((50, 50), content, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def setup_processed_document(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={"email": "reviewer@db.edu", "password": "Password12345!"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    proj = client.post("/api/v1/projects", json={"name": "DBMS Advanced"}, headers=headers).json()
    doc = client.post(
        f"/api/v1/projects/{proj['id']}/documents",
        files={"file": ("dbms.pdf", create_sample_pdf(), "application/pdf")},
        headers=headers,
    ).json()
    doc_id = doc["id"]

    client.post(f"/api/v1/documents/{doc_id}/confirm-extraction", headers=headers)
    questions = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers).json()

    # Process first question
    proc_res = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [questions[0]["id"]]},
        headers={**headers, "Idempotency-Key": "prog-key-1"},
    ).json()
    job_id = proc_res["jobs"][0]["id"]

    # Execute
    client.post(f"/api/v1/jobs/{job_id}/execute", headers=headers)

    return headers, doc_id, questions[0]["id"], questions[1]["id"]


def test_document_progress_and_sse_events(client: TestClient):
    headers, doc_id, q1_id, q2_id = setup_processed_document(client)

    # 1. Progress endpoint
    prog_res = client.get(f"/api/v1/documents/{doc_id}/progress", headers=headers)
    assert prog_res.status_code == 200
    prog = prog_res.json()
    assert prog["total"] == 2
    assert prog["counts"]["VERIFIER_APPROVED"] == 1
    assert prog["counts"]["PENDING"] == 1
    assert prog["completed"] == 1
    assert prog["percent"] == 50.0

    # 2. SSE events endpoint
    sse_res = client.get(f"/api/v1/documents/{doc_id}/events", headers=headers)
    assert sse_res.status_code == 200
    assert "text/event-stream" in sse_res.headers["content-type"]
    assert "event: progress" in sse_res.text
    assert "VERIFIER_APPROVED" in sse_res.text


def test_answer_history_edit_and_human_approval(client: TestClient):
    headers, doc_id, q1_id, _ = setup_processed_document(client)

    # 1. Get latest answer
    ans_res = client.get(f"/api/v1/questions/{q1_id}/answer", headers=headers)
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert ans_data["version_number"] == 1
    assert ans_data["verifier_report"]["verdict"] == "approved"
    v1_id = ans_data["answer_version_id"]

    # 2. Human reviewer approves version 1
    appr_res = client.post(
        f"/api/v1/questions/{q1_id}/approve",
        json={"answer_version_id": v1_id, "decision": "APPROVED"},
        headers=headers,
    )
    assert appr_res.status_code == 201

    # Check approvals list
    list_appr = client.get(f"/api/v1/questions/{q1_id}/approvals", headers=headers)
    assert list_appr.status_code == 200
    assert len(list_appr.json()) == 1
    assert list_appr.json()[0]["decision"] == "APPROVED"

    # 3. User edits answer -> creates new version 2 (immutable history)
    edited_body = {
        "answer": {
            "introduction": "Updated ACID introduction with strict isolation explanation.",
            "sections": [
                {
                    "heading": "Atomicity",
                    "content": "All or nothing execution guarantee.",
                    "bullets": ["Rollback on abort", "Commit writes changes"],
                    "formula": None,
                    "example": "Bank fund transfer",
                }
            ],
            "conclusion": "ACID properties maintain database consistency.",
            "diagram_source": None,
        }
    }
    patch_res = client.patch(f"/api/v1/questions/{q1_id}/answer", json=edited_body, headers=headers)
    assert patch_res.status_code == 201
    assert patch_res.json()["version_number"] == 2

    # 4. Check version history: must have both version 1 and version 2
    versions_res = client.get(f"/api/v1/questions/{q1_id}/versions", headers=headers)
    assert versions_res.status_code == 200
    versions = versions_res.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 1
    assert versions[1]["version_number"] == 2
    # Prior version 1 still retains its human approval
    assert len(versions[0]["human_approvals"]) == 1
    # Version 2 is clean without approvals
    assert len(versions[1]["human_approvals"]) == 0
