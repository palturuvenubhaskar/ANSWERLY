from pathlib import Path
import io
import fitz
import pytest
from fastapi.testclient import TestClient


def create_duplicate_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    content = """UNIT 1: ALGORITHMS
Q1. Explain asymptotic notations and Big-O notation with examples. [10 Marks]
Q2. What are the advantages of divide and conquer technique? (5 Marks)
Q3. Explain asymptotic notation and Big O notation with suitable example. [10 Marks]
"""
    page.insert_text((50, 50), content, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_question_crud_and_preservation_of_original_text(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={"email": "student@college.edu", "password": "SafePassword123!"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    proj = client.post("/api/v1/projects", json={"name": "OS Prep"}, headers=headers).json()
    proj_id = proj["id"]

    # Create question
    create_res = client.post(
        f"/api/v1/projects/{proj_id}/questions",
        json={"question_text": "What is a deadlock and what are its four necessary conditions?", "marks": 10},
        headers=headers,
    )
    assert create_res.status_code == 201
    q_id = create_res.json()["id"]

    # Retrieve question
    get_res = client.get(f"/api/v1/questions/{q_id}", headers=headers)
    assert get_res.status_code == 200
    q_data = get_res.json()
    assert q_data["original_text"] == "What is a deadlock and what are its four necessary conditions?"

    # Update question wording and marks
    patch_res = client.patch(
        f"/api/v1/questions/{q_id}",
        json={"question_text": "Define deadlock. Explain Coffman's four conditions in detail.", "marks": 12},
        headers=headers,
    )
    assert patch_res.status_code == 200
    patched = patch_res.json()
    assert patched["question_text"] == "Define deadlock. Explain Coffman's four conditions in detail."
    assert patched["marks"] == 12
    # CRITICAL: original_text must remain unchanged
    assert patched["original_text"] == "What is a deadlock and what are its four necessary conditions?"

    # Delete question
    del_res = client.delete(f"/api/v1/questions/{q_id}", headers=headers)
    assert del_res.status_code == 204
    assert client.get(f"/api/v1/questions/{q_id}", headers=headers).status_code == 404


def test_question_reordering_and_duplicate_detection(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={"email": "prof_algo@test.org", "password": "SecurePassword123!"}).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    proj = client.post("/api/v1/projects", json={"name": "Algorithm Design"}, headers=headers).json()
    proj_id = proj["id"]

    pdf_bytes = create_duplicate_pdf()
    doc_res = client.post(
        f"/api/v1/projects/{proj_id}/documents",
        files={"file": ("algo_dup.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    q_list_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers)
    assert q_list_res.status_code == 200
    questions = q_list_res.json()
    assert len(questions) == 3

    q1_id = questions[0]["id"]
    q2_id = questions[1]["id"]
    q3_id = questions[2]["id"]

    # 1. Test duplicate detection
    dup_res = client.get(f"/api/v1/documents/{doc_id}/duplicates", headers=headers)
    assert dup_res.status_code == 200
    duplicates = dup_res.json()
    assert len(duplicates) >= 1
    # Check that Q1 and Q3 are suggested as duplicates
    pair = duplicates[0]
    matched_ids = {pair["question_id_1"], pair["question_id_2"]}
    assert q1_id in matched_ids and q3_id in matched_ids
    assert pair["similarity"] >= 0.80

    # 2. Test reordering questions (reverse order: q3, q2, q1)
    reorder_res = client.post(
        f"/api/v1/documents/{doc_id}/questions/reorder",
        json={"ordered_question_ids": [q3_id, q2_id, q1_id]},
        headers=headers,
    )
    assert reorder_res.status_code == 200

    # Verify new positions
    reordered_list = client.get(f"/api/v1/documents/{doc_id}/questions", headers=headers).json()
    assert reordered_list[0]["id"] == q3_id
    assert reordered_list[0]["position"] == 1
    assert reordered_list[1]["id"] == q2_id
    assert reordered_list[1]["position"] == 2
    assert reordered_list[2]["id"] == q1_id
    assert reordered_list[2]["position"] == 3

    # Reorder with invalid ID list returns 400
    invalid_reorder = client.post(
        f"/api/v1/documents/{doc_id}/questions/reorder",
        json={"ordered_question_ids": [q3_id, q2_id]},
        headers=headers,
    )
    assert invalid_reorder.status_code == 400
