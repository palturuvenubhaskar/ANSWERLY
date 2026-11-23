import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.storage import StorageService

def register_user(client: TestClient, email: str, password: str = "StrongP@ssw0rd123!"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def login_user(client: TestClient, email: str, password: str = "StrongP@ssw0rd123!"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_auth_flow_and_duplicate_rejection(client: TestClient):
    email = "testuser1@example.com"
    res1 = register_user(client, email)
    assert res1.status_code == 201
    data1 = res1.json()
    assert "access_token" in data1
    assert data1["token_type"] == "bearer"

    # Duplicate registration
    res2 = register_user(client, email)
    assert res2.status_code == 409

    # Valid login
    res3 = login_user(client, email)
    assert res3.status_code == 200
    assert "access_token" in res3.json()

    # Invalid login
    res4 = login_user(client, email, "WrongPassword123!")
    assert res4.status_code == 401


def test_project_crud_and_cross_user_isolation(client: TestClient):
    # User A
    user_a = register_user(client, "usera@example.com").json()
    token_a = user_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B
    user_b = register_user(client, "userb@example.com").json()
    token_b = user_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a project
    create_res = client.post(
        "/api/v1/projects",
        json={"name": "Compiler Design", "description": "Exam QB 2026"},
        headers=headers_a,
    )
    assert create_res.status_code == 201
    project_a = create_res.json()
    proj_id = project_a["id"]
    assert project_a["name"] == "Compiler Design"

    # User A gets project details
    get_res = client.get(f"/api/v1/projects/{proj_id}", headers=headers_a)
    assert get_res.status_code == 200
    assert get_res.json()["question_count"] == 0

    # User A updates project
    patch_res = client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"name": "Compiler Design - Revised"},
        headers=headers_a,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Compiler Design - Revised"

    # User B tries to access User A's project -> 404
    b_get = client.get(f"/api/v1/projects/{proj_id}", headers=headers_b)
    assert b_get.status_code == 404

    # User B tries to update User A's project -> 404
    b_patch = client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"name": "Hijacked"},
        headers=headers_b,
    )
    assert b_patch.status_code == 404

    # User B tries to delete User A's project -> 404
    b_del = client.request(
        "DELETE",
        f"/api/v1/projects/{proj_id}",
        json={"confirm": True},
        headers=headers_b,
    )
    assert b_del.status_code == 404

    # User A deletes project without confirm -> 400
    a_del_noconfirm = client.request(
        "DELETE",
        f"/api/v1/projects/{proj_id}",
        json={"confirm": False},
        headers=headers_a,
    )
    assert a_del_noconfirm.status_code == 400

    # User A deletes project with confirm -> 204
    a_del = client.request(
        "DELETE",
        f"/api/v1/projects/{proj_id}",
        json={"confirm": True},
        headers=headers_a,
    )
    assert a_del.status_code == 204

    # Subsequent get returns 404
    assert client.get(f"/api/v1/projects/{proj_id}", headers=headers_a).status_code == 404


def test_storage_service(tmp_path):
    storage = StorageService(base_dir=tmp_path)
    sample_content = b"Answerly test content for storage."

    stored = storage.save(sample_content, extension="txt")
    assert stored.size_bytes == len(sample_content)
    assert storage.exists(stored.storage_key)

    retrieved = storage.get(stored.storage_key)
    assert retrieved == sample_content

    # Path traversal rejection
    with pytest.raises(ValueError, match="Invalid storage key|Path traversal"):
        storage.get("../secret.txt")

    # Delete
    assert storage.delete(stored.storage_key) is True
    assert storage.exists(stored.storage_key) is False
