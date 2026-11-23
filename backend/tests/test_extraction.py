import io
from pathlib import Path
import fitz
from docx import Document as DocxDocument
import pytest
from fastapi.testclient import TestClient


def create_sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    content = """UNIT 1: INTRODUCTION TO ALGORITHMS
Q1. Define asymptotic notations and explain Big-O with an example. [10 Marks] [BL: L2] [CO1]
Q2. What is Divide and Conquer? List its advantages. (5 Marks) [BL: L1] [CO1]
UNIT 2: GRAPH ALGORITHMS
Q3. Explain Dijkstra's algorithm for finding single-source shortest paths. [10M] [BL: L3] [CO2]
"""
    page.insert_text((50, 50), content, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_sample_docx() -> bytes:
    doc = DocxDocument()
    doc.add_paragraph("UNIT 1: DATABASE ARCHITECTURE")
    doc.add_paragraph("1. Explain the 3-schema architecture of DBMS. [10 Marks] [BL: L2]")
    doc.add_paragraph("2. Differentiate between DDL and DML commands with syntax. (5M) [CO1]")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_document_pdf_upload_and_extraction(client: TestClient):
    # Register and create project
    reg = client.post("/api/v1/auth/register", json={"email": "prof@university.edu", "password": "Password12345!"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    proj = client.post("/api/v1/projects", json={"name": "DAA Course"}, headers=headers).json()
    proj_id = proj["id"]

    # 1. Invalid file rejection (wrong MIME)
    fake_pdf = b"This is not a real PDF file header"
    res_fake = client.post(
        f"/api/v1/projects/{proj_id}/documents",
        files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert res_fake.status_code == 400

    # 2. Valid PDF upload
    pdf_bytes = create_sample_pdf()
    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/documents",
        files={"file": ("daa_qb.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["title"] == "daa_qb.pdf"
    assert doc_data["file_size_bytes"] == len(pdf_bytes)
    assert doc_data["sha256"] is not None

    # 3. Retrieve document metadata
    get_res = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == doc_id

    # 4. List extracted questions
    q_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers)
    assert q_res.status_code == 200
    questions = q_res.json()
    assert len(questions) == 3

    # Check question 1 metadata
    q1 = questions[0]
    assert "asymptotic notations" in q1["question_text"].lower()
    assert q1["marks"] == 10
    assert q1["bl"] == "L2"
    assert q1["co"] == "CO1"
    assert q1["source_page_start"] == 1
    assert q1["original_text"] is not None

    # Check question 2
    q2 = questions[1]
    assert "divide and conquer" in q2["question_text"].lower()
    assert q2["marks"] == 5
    assert q2["bl"] == "L1"

    # Check question 3
    q3 = questions[2]
    assert "dijkstra" in q3["question_text"].lower()
    assert q3["marks"] == 10
    assert q3["bl"] == "L3"

    # 5. Confirm extraction
    confirm_res = client.post(f"/api/v1/documents/{doc_id}/confirm-extraction", headers=headers)
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "READY"


def test_document_docx_upload_and_extraction(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={"email": "docx_user@test.org", "password": "SecurePassword123!"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    proj = client.post("/api/v1/projects", json={"name": "DBMS Exam"}, headers=headers).json()
    proj_id = proj["id"]

    docx_bytes = create_sample_docx()
    upload_res = client.post(
        f"/api/v1/projects/{proj_id}/documents",
        files={"file": ("dbms.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    q_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers)
    assert q_res.status_code == 200
    questions = q_res.json()
    assert len(questions) == 2
    assert "3-schema architecture" in questions[0]["question_text"]
    assert questions[0]["marks"] == 10
    assert questions[1]["marks"] == 5


def test_document_cross_user_isolation(client: TestClient):
    user_a = client.post("/api/v1/auth/register", json={"email": "alice@corp.com", "password": "Password123!"}).json()
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}

    user_b = client.post("/api/v1/auth/register", json={"email": "bob@corp.com", "password": "Password123!"}).json()
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    proj = client.post("/api/v1/projects", json={"name": "Alice Private Project"}, headers=headers_a).json()
    pdf_bytes = create_sample_pdf()
    doc = client.post(
        f"/api/v1/projects/{proj['id']}/documents",
        files={"file": ("alice.pdf", pdf_bytes, "application/pdf")},
        headers=headers_a,
    ).json()

    doc_id = doc["id"]

    # Bob cannot view document
    assert client.get(f"/api/v1/documents/{doc_id}", headers=headers_b).status_code == 404

    # Bob cannot view questions
    assert client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers_b).status_code == 404

    # Bob cannot confirm extraction
    assert client.post(f"/api/v1/documents/{doc_id}/confirm-extraction", headers=headers_b).status_code == 404
