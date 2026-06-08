import hashlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from ragmax.core.exceptions import InvalidRequestError


@dataclass(frozen=True)
class StoredSourceFile:
    filename: str
    path: Path
    storage_key: str
    size_bytes: int
    sha256: str


class LocalSourceStorage:
    def __init__(self, *, root_dir: Path, max_upload_bytes: int) -> None:
        self._root_dir = root_dir
        self._max_upload_bytes = max_upload_bytes

    async def save_upload(self, *, source_id: str, upload: UploadFile) -> StoredSourceFile:
        filename = _safe_path_part(upload.filename or "upload")
        safe_source_id = _safe_path_part(source_id)
        source_dir = self._root_dir / safe_source_id
        path = source_dir / filename

        content = await upload.read()
        size_bytes = len(content)
        if size_bytes == 0:
            raise InvalidRequestError("Uploaded file is empty.")
        if size_bytes > self._max_upload_bytes:
            raise InvalidRequestError("Uploaded file exceeds the configured size limit.")

        source_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

        return StoredSourceFile(
            filename=filename,
            path=path,
            storage_key=f"{safe_source_id}/{filename}",
            size_bytes=size_bytes,
            sha256=hashlib.sha256(content).hexdigest(),
        )


def _safe_path_part(value: str) -> str:
    path_name = Path(value).name.strip()
    if not path_name or path_name in {".", ".."}:
        raise InvalidRequestError("Invalid upload path.")
    return path_name
