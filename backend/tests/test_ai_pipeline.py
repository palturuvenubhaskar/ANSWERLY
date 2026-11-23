import io
import fitz
import pytest
from fastapi.testclient import TestClient

from app.gateway import MockDeterministicGateway
from app.pipeline import execute_job


def create_sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    content = """UNIT 1: NETWORKING
Q1. Explain the OSI 7-layer reference model in detail. [10 Marks]
Q2. What is TCP three-way handshake? (5 Marks)
"""
    page.insert_text((50, 50), content, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def setup_ready_document(client: TestClient, email: str = "ai_student@univ.edu"):
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": "SecurePassword123!"}).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    proj = client.post("/api/v1/projects", json={"name": "Computer Networks"}, headers=headers).json()
    proj_id = proj["id"]

    pdf_bytes = create_sample_pdf()
    doc = client.post(
        f"/api/v1/projects/{proj_id}/documents",
        files={"file": ("networks.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    ).json()
    doc_id = doc["id"]

    # Confirm extraction
    client.post(f"/api/v1/documents/{doc_id}/confirm-extraction", headers=headers)

    questions = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers).json()
    return headers, proj_id, doc_id, questions


def test_batch_idempotency_and_conflict(client: TestClient):
    headers, proj_id, doc_id, questions = setup_ready_document(client, "idemp_user@test.org")
    q1_id = questions[0]["id"]
    q2_id = questions[1]["id"]

    # 1. Missing Idempotency-Key returns 400
    res_no_key = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [q1_id]},
        headers=headers,
    )
    assert res_no_key.status_code == 400

    # 2. Valid processing start
    key = "idem-key-batch-001"
    res1 = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [q1_id, q2_id]},
        headers={**headers, "Idempotency-Key": key},
    )
    assert res1.status_code == 201
    run1 = res1.json()
    assert len(run1["jobs"]) == 2
    job_ids = [j["id"] for j in run1["jobs"]]

    # 3. Repeat exact same request with same key -> returns existing run (idempotent 200/201)
    res2 = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [q1_id, q2_id]},
        headers={**headers, "Idempotency-Key": key},
    )
    assert res2.status_code in (200, 201)
    run2 = res2.json()
    assert run2["id"] == run1["id"]
    assert [j["id"] for j in run2["jobs"]] == job_ids

    # 4. Reuse same key with different questions -> 409 Conflict
    res3 = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [q1_id]},
        headers={**headers, "Idempotency-Key": key},
    )
    assert res3.status_code == 409


def test_pipeline_execution_approval_and_revision_state_machine(client: TestClient):
    headers, proj_id, doc_id, questions = setup_ready_document(client, "eval_user@test.org")
    q1_id = questions[0]["id"]

    # Start processing for Q1
    res = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [q1_id]},
        headers={**headers, "Idempotency-Key": "key-pass-test"},
    )
    assert res.status_code == 201
    job_id = res.json()["jobs"][0]["id"]

    # Execute job with passing gateway
    exec_res = client.post(f"/api/v1/jobs/{job_id}/execute", headers=headers)
    assert exec_res.status_code == 200
    job_data = exec_res.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["revision_count"] == 0

    # Verify Question is VERIFIER_APPROVED
    q_data = client.get(f"/api/v1/questions/{q1_id}", headers=headers).json()
    assert q_data["status"] == "VERIFIER_APPROVED"


def test_revision_and_max_two_revisions_cap(client: TestClient, db_session):
    headers, proj_id, doc_id, questions = setup_ready_document(client, "cap_user@test.org")
    q2_id = questions[1]["id"]

    res = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [q2_id]},
        headers={**headers, "Idempotency-Key": "key-fail-test"},
    )
    job_id = res.json()["jobs"][0]["id"]

    # Execute with always_fail gateway -> should cap at 2 revisions and transition to MANUAL_REVIEW
    always_fail_gw = MockDeterministicGateway(mode="always_fail")
    final_job = execute_job(job_id, db_session, gateway=always_fail_gw)
    assert final_job.revision_count == 2
    assert final_job.status == "MANUAL_REVIEW"

    # Verify question status in API
    q_data = client.get(f"/api/v1/questions/{q2_id}", headers=headers).json()
    assert q_data["status"] == "MANUAL_REVIEW"


def test_job_cancellation(client: TestClient):
    headers, proj_id, doc_id, questions = setup_ready_document(client, "cancel_user@test.org")
    q_id = questions[0]["id"]

    res = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [q_id]},
        headers={**headers, "Idempotency-Key": "key-cancel-test"},
    )
    job_id = res.json()["jobs"][0]["id"]

    # Request cancel
    cancel_res = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["cancel_requested"] is True
    assert cancel_res.json()["status"] == "CANCELLED"
