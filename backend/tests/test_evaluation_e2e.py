import io
from datetime import timedelta
import fitz
import pytest
from fastapi.testclient import TestClient

from app.models import utc_now


def create_evaluation_ai_qb_pdf() -> bytes:
    doc = fitz.open()
    page1 = doc.new_page()
    content1 = """UNIT I: INTRODUCTION TO ARTIFICIAL INTELLIGENCE
Q1. Define Artificial Intelligence and differentiate between Strong AI and Weak AI. [5 Marks] [BL: L1] [CO1]

UNIT II: SEARCH ALGORITHMS
Q2. Explain Breadth-First Search (BFS) and Depth-First Search (DFS) with a comparative example. [10 Marks] [BL: L2] [CO2]
"""
    page1.insert_text((50, 50), content1, fontsize=11)

    page2 = doc.new_page()
    content2 = """UNIT III: PROBABILISTIC REASONING
Q3. State and derive Bayes' Theorem. Explain its application in probabilistic reasoning. [10 Marks] [BL: L3] [CO3]

UNIT IV: MACHINE LEARNING
Q4. Explain Decision Tree learning, Entropy, and Information Gain with mathematical formulas. [10 Marks] [BL: L3] [CO4]

UNIT V: EXPERT SYSTEMS
Q5. Describe the architecture of an Expert System with reference to MYCIN rule-based reasoning. [10 Marks] [BL: L2] [CO5]
"""
    page2.insert_text((50, 50), content2, fontsize=11)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_evaluation_end_to_end_lifecycle(client: TestClient, db_session):
    # 1. Register user
    reg = client.post("/api/v1/auth/register", json={"email": "eval_lead@university.edu", "password": "ReleasePassword2026!"}).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create project
    proj = client.post(
        "/api/v1/projects",
        json={"name": "Artificial Intelligence Question Bank 2026", "description": "Accreditation Eval Set"},
        headers=headers,
    ).json()
    proj_id = proj["id"]

    # 3. Add Reference Excerpt
    ref_res = client.post(
        f"/api/v1/projects/{proj_id}/references",
        json={
            "title": "Russell & Norvig AI A Modern Approach 4th Ed",
            "text": "Bayes theorem relates the conditional and marginal probabilities of stochastic events A and B: P(A|B) = P(B|A)P(A)/P(B).",
            "source_label": "AIMA-Ch13",
            "page": 492,
        },
        headers=headers,
    )
    assert ref_res.status_code == 201
    ref_id = ref_res.json()["id"]

    # 4. Upload Labeled AI Question Bank PDF
    pdf_bytes = create_evaluation_ai_qb_pdf()
    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/documents",
        files={"file": ("AI_Evaluation_QB.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc = upload_res.json()
    doc_id = doc["id"]

    # 5. Verify Extraction Recall & Metadata (Release Gate 1: No silent drops)
    q_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers)
    assert q_res.status_code == 200
    questions = q_res.json()

    # All 5 units and questions must be present
    assert len(questions) == 5, "Release Gate Failed: Silent question drop detected"
    assert questions[0]["marks"] == 5
    assert questions[0]["bl"] == "L1"
    assert questions[0]["co"] == "CO1"
    assert "artificial intelligence" in questions[0]["question_text"].lower()

    assert questions[1]["marks"] == 10
    assert "breadth-first search" in questions[1]["question_text"].lower()

    assert questions[2]["marks"] == 10
    assert "bayes" in questions[2]["question_text"].lower()

    assert questions[3]["marks"] == 10
    assert "decision tree" in questions[3]["question_text"].lower()

    assert questions[4]["marks"] == 10
    assert "expert system" in questions[4]["question_text"].lower()

    # 6. Confirm extraction review
    confirm = client.post(f"/api/v1/documents/{doc_id}/confirm-extraction", headers=headers)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "READY"

    # 7. Start batch processing with idempotency
    idemp_key = "eval-run-2026-release"
    proc_res = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"reference_ids": [ref_id]},
        headers={**headers, "Idempotency-Key": idemp_key},
    )
    assert proc_res.status_code == 201
    run_data = proc_res.json()
    assert len(run_data["jobs"]) == 5

    # 8. Execute all 5 question jobs
    for job in run_data["jobs"]:
        exec_res = client.post(f"/api/v1/jobs/{job['id']}/execute", headers=headers)
        assert exec_res.status_code == 200
        assert exec_res.json()["status"] == "COMPLETED"

    # 9. Check progress dashboard
    prog = client.get(f"/api/v1/documents/{doc_id}/progress", headers=headers).json()
    assert prog["total"] == 5
    assert prog["completed"] == 5
    assert prog["percent"] == 100.0
    assert prog["counts"]["VERIFIER_APPROVED"] == 5

    # 10. Audit Answer, Verifier Report, and Human Review on Q3 (Bayes' Theorem)
    q3_id = questions[2]["id"]
    ans3 = client.get(f"/api/v1/questions/{q3_id}/answer", headers=headers).json()
    assert ans3["version_number"] == 1
    assert ans3["verifier_report"]["verdict"] == "approved"
    assert len(ans3["verifier_report"]["criteria"]) == 7

    # Record human decision
    appr_res = client.post(
        f"/api/v1/questions/{q3_id}/approve",
        json={"answer_version_id": ans3["answer_version_id"], "decision": "APPROVED"},
        headers=headers,
    )
    assert appr_res.status_code == 201

    # 11. Validate All 4 Export Formats (Release Gate 2: Structural validation)
    # Markdown
    exp_md = client.post(f"/api/v1/documents/{doc_id}/exports", json={"format": "md"}, headers=headers).json()
    dl_md = client.get(exp_md["download_url"], headers=headers)
    assert dl_md.status_code == 200
    assert "AI_Evaluation_QB.pdf" in dl_md.text
    assert "Artificial Intelligence" in dl_md.text

    # JSON
    exp_json = client.post(f"/api/v1/documents/{doc_id}/exports", json={"format": "json"}, headers=headers).json()
    dl_json = client.get(exp_json["download_url"], headers=headers)
    assert dl_json.status_code == 200
    assert dl_json.json()["question_count"] == 5

    # DOCX
    exp_docx = client.post(f"/api/v1/documents/{doc_id}/exports", json={"format": "docx"}, headers=headers).json()
    dl_docx = client.get(exp_docx["download_url"], headers=headers)
    assert dl_docx.status_code == 200
    assert dl_docx.content.startswith(b"PK\x03\x04")

    # PDF
    exp_pdf = client.post(f"/api/v1/documents/{doc_id}/exports", json={"format": "pdf"}, headers=headers).json()
    dl_pdf = client.get(exp_pdf["download_url"], headers=headers)
    assert dl_pdf.status_code == 200
    assert dl_pdf.content.startswith(b"%PDF-")

    # 12. Retention Policy Sweep
    sweep_res = client.post("/api/v1/system/retention-sweep", headers=headers)
    assert sweep_res.status_code == 200
    assert sweep_res.json()["status"] == "success"
