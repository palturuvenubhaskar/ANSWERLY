import io
import fitz
import pytest
from fastapi.testclient import TestClient


def create_sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    content = """UNIT 1: SOFTWARE ENGINEERING
Q1. Explain the Agile manifesto and Scrum framework. [10 Marks]
Q2. What is Cyclomatic Complexity? (5 Marks)
"""
    page.insert_text((50, 50), content, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def setup_exportable_document(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={"email": "exporter@college.edu", "password": "Password12345!"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    proj = client.post("/api/v1/projects", json={"name": "Software Engineering"}, headers=headers).json()
    doc = client.post(
        f"/api/v1/projects/{proj['id']}/documents",
        files={"file": ("se_qb.pdf", create_sample_pdf(), "application/pdf")},
        headers=headers,
    ).json()
    doc_id = doc["id"]

    client.post(f"/api/v1/documents/{doc_id}/confirm-extraction", headers=headers)
    questions = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers).json()

    # Process and approve Q1 only
    proc_res = client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"question_ids": [questions[0]["id"]]},
        headers={**headers, "Idempotency-Key": "export-key-1"},
    ).json()
    job_id = proc_res["jobs"][0]["id"]
    client.post(f"/api/v1/jobs/{job_id}/execute", headers=headers)

    return headers, doc_id, questions[0]["id"], questions[1]["id"]


def test_markdown_and_json_exports(client: TestClient):
    headers, doc_id, q1_id, q2_id = setup_exportable_document(client)

    # 1. Export Markdown (default: only approved answers)
    exp_md_res = client.post(
        f"/api/v1/documents/{doc_id}/exports",
        json={"format": "md", "include_unapproved": False},
        headers=headers,
    )
    assert exp_md_res.status_code == 201
    md_meta = exp_md_res.json()
    assert md_meta["included_question_count"] == 1
    assert md_meta["format"] == "MD"

    # Download MD content
    dl_md = client.get(md_meta["download_url"], headers=headers)
    assert dl_md.status_code == 200
    assert "Agile manifesto" in dl_md.text
    # Q2 should be excluded because it's unapproved
    assert "Cyclomatic Complexity" not in dl_md.text

    # 2. Export JSON with include_unapproved=True
    exp_json_res = client.post(
        f"/api/v1/documents/{doc_id}/exports",
        json={"format": "json", "include_unapproved": True},
        headers=headers,
    )
    assert exp_json_res.status_code == 201
    json_meta = exp_json_res.json()
    assert json_meta["included_question_count"] == 2

    dl_json = client.get(json_meta["download_url"], headers=headers)
    assert dl_json.status_code == 200
    data = dl_json.json()
    assert data["question_count"] == 2
    assert data["items"][0]["is_unapproved"] is False
    assert data["items"][1]["is_unapproved"] is True


def test_docx_and_pdf_exports(client: TestClient):
    headers, doc_id, q1_id, q2_id = setup_exportable_document(client)

    # 1. Export DOCX
    exp_docx = client.post(
        f"/api/v1/documents/{doc_id}/exports",
        json={"format": "docx", "include_unapproved": True},
        headers=headers,
    ).json()
    dl_docx = client.get(exp_docx["download_url"], headers=headers)
    assert dl_docx.status_code == 200
    # Valid DOCX starts with PK zip header
    assert dl_docx.content.startswith(b"PK\x03\x04")

    # 2. Export PDF
    exp_pdf = client.post(
        f"/api/v1/documents/{doc_id}/exports",
        json={"format": "pdf", "include_unapproved": True},
        headers=headers,
    ).json()
    dl_pdf = client.get(exp_pdf["download_url"], headers=headers)
    assert dl_pdf.status_code == 200
    # Valid PDF starts with %PDF- header
    assert dl_pdf.content.startswith(b"%PDF-")


def test_export_cross_user_isolation(client: TestClient):
    headers_a, doc_id, _, _ = setup_exportable_document(client)

    # User B
    user_b = client.post("/api/v1/auth/register", json={"email": "intruder@univ.edu", "password": "Password12345!"}).json()
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    exp = client.post(
        f"/api/v1/documents/{doc_id}/exports",
        json={"format": "json"},
        headers=headers_a,
    ).json()
    exp_id = exp["id"]

    # User B cannot read or download User A's export
    assert client.get(f"/api/v1/exports/{exp_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/exports/{exp_id}/download", headers=headers_b).status_code == 404
