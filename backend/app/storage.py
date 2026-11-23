import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

STORAGE_BASE_DIR = Path(os.getenv("LOCAL_STORAGE_PATH", "./storage")).resolve()


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    sha256: str
    size_bytes: int
    path: Path


class StorageService:
    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir).resolve() if base_dir else STORAGE_BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        # Sanitize against path traversal: allow only safe alphanumeric + dash + underscore
        safe_key = os.path.basename(storage_key)
        if safe_key != storage_key or ".." in storage_key or "/" in storage_key or "\\" in storage_key:
            raise ValueError("Invalid storage key")
        full_path = (self.base_dir / safe_key).resolve()
        if not full_path.is_relative_to(self.base_dir):
            raise ValueError("Path traversal detected")
        return full_path

    def save(self, content: bytes, extension: str = "") -> StoredFile:
        ext = extension.strip()
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        # Keep extension clean (alphanumeric only)
        ext = "".join(ch for ch in ext if ch.isalnum() or ch == ".")
        storage_key = f"{uuid4().hex}{ext}"
        target_path = self.base_dir / storage_key

        sha256 = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)

        with open(target_path, "wb") as f:
            f.write(content)

        return StoredFile(
            storage_key=storage_key,
            sha256=sha256,
            size_bytes=size_bytes,
            path=target_path,
        )

    def get(self, storage_key: str) -> bytes:
        path = self._resolve_key(storage_key)
        if not path.exists():
            raise FileNotFoundError(f"File with key {storage_key} not found")
        return path.read_bytes()

    def delete(self, storage_key: str) -> bool:
        path = self._resolve_key(storage_key)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        path = self._resolve_key(storage_key)
        return path.exists()


storage_service = StorageService()
