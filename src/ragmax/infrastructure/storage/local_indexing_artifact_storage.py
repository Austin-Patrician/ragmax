import gzip
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio

from ragmax.core.exceptions import InvalidRequestError, NotFoundError


@dataclass(frozen=True)
class StoredIndexingArtifact:
    storage_uri: str
    payload_format: str
    size_bytes: int
    sha256: str
    record_count: int
    preview: dict[str, Any]


class LocalIndexingArtifactStorage:
    def __init__(self, *, root_dir: Path, preview_limit: int = 5) -> None:
        self._root_dir = root_dir
        self._preview_limit = preview_limit

    def write_json(
        self,
        *,
        source_id: str,
        run_id: str,
        stage_run_id: str,
        stage_name: str,
        artifact_type: str,
        payload: dict[str, Any],
    ) -> StoredIndexingArtifact:
        storage_uri = self._build_uri(
            source_id,
            run_id,
            stage_name,
            stage_run_id,
            artifact_type,
            "json",
        )
        path = self._path_for_uri(storage_uri)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        path.write_bytes(encoded)
        return StoredIndexingArtifact(
            storage_uri=storage_uri,
            payload_format="json",
            size_bytes=len(encoded),
            sha256=hashlib.sha256(encoded).hexdigest(),
            record_count=1,
            preview=payload,
        )

    def write_jsonl(
        self,
        *,
        source_id: str,
        run_id: str,
        stage_run_id: str,
        stage_name: str,
        artifact_type: str,
        records: list[dict[str, Any]],
        compress: bool = False,
    ) -> StoredIndexingArtifact:
        extension = "jsonl.gz" if compress else "jsonl"
        payload_format = "jsonl.gz" if compress else "jsonl"
        storage_uri = self._build_uri(
            source_id,
            run_id,
            stage_name,
            stage_run_id,
            artifact_type,
            extension,
        )
        path = self._path_for_uri(storage_uri)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
        encoded = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        if compress:
            encoded = gzip.compress(encoded)
        path.write_bytes(encoded)
        return StoredIndexingArtifact(
            storage_uri=storage_uri,
            payload_format=payload_format,
            size_bytes=len(encoded),
            sha256=hashlib.sha256(encoded).hexdigest(),
            record_count=len(records),
            preview={"records": records[: self._preview_limit]},
        )

    def read_json(self, storage_uri: str) -> dict[str, Any]:
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            raise NotFoundError(f"Indexing artifact not found: {storage_uri}")
        return json.loads(path.read_text(encoding="utf-8"))

    def read_jsonl(
        self,
        storage_uri: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], bool]:
        if offset < 0 or limit <= 0:
            raise InvalidRequestError("offset must be >= 0 and limit must be > 0.")

        path = self._path_for_uri(storage_uri)
        if not path.exists():
            raise NotFoundError(f"Indexing artifact not found: {storage_uri}")

        opener = gzip.open if storage_uri.endswith(".gz") else open
        records: list[dict[str, Any]] = []
        seen = 0
        has_more = False
        with opener(path, "rt", encoding="utf-8") as file_handle:
            for line in file_handle:
                if not line.strip():
                    continue
                if seen < offset:
                    seen += 1
                    continue
                if len(records) >= limit:
                    has_more = True
                    break
                records.append(json.loads(line))
                seen += 1
        return records, has_more

    async def delete_source(self, source_id: str) -> bool:
        return await anyio.to_thread.run_sync(self._delete_source_sync, source_id)

    def _delete_source_sync(self, source_id: str) -> bool:
        source_dir = self._source_dir_for(source_id)
        if not source_dir.exists():
            return False
        if source_dir.is_dir():
            shutil.rmtree(source_dir)
        else:
            source_dir.unlink()
        return True

    def _build_uri(
        self,
        source_id: str,
        run_id: str,
        stage_name: str,
        stage_run_id: str,
        artifact_type: str,
        extension: str,
    ) -> str:
        return "/".join(
            [
                _safe_path_part(source_id),
                _safe_path_part(run_id),
                _safe_path_part(stage_name),
                _safe_path_part(stage_run_id),
                f"{_safe_path_part(artifact_type)}.{extension}",
            ]
        )

    def _path_for_uri(self, storage_uri: str) -> Path:
        parts = [
            _safe_path_part(part)
            for part in storage_uri.replace("\\", "/").split("/")
            if part
        ]
        if not parts:
            raise InvalidRequestError("Invalid indexing artifact path.")
        path = self._root_dir.joinpath(*parts)
        root = self._root_dir.resolve()
        resolved = path.resolve()
        if resolved != root and root not in resolved.parents:
            raise InvalidRequestError("Invalid indexing artifact path.")
        return resolved

    def _source_dir_for(self, source_id: str) -> Path:
        path = self._root_dir / _safe_path_part(source_id)
        root = self._root_dir.resolve()
        resolved = path.resolve()
        if resolved != root and root not in resolved.parents:
            raise InvalidRequestError("Invalid indexing artifact path.")
        return resolved


def _safe_path_part(value: str) -> str:
    path_name = Path(value).name.strip()
    if not path_name or path_name in {".", ".."}:
        raise InvalidRequestError("Invalid indexing artifact path.")
    return path_name
