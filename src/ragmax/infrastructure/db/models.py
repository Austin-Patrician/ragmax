from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ragmax.infrastructure.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class SourceModel(Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    notebook_id: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    media_type: Mapped[str] = mapped_column(String(128))
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str | None] = mapped_column(Text)
    blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    file_size: Mapped[int | None] = mapped_column(Integer)
    source_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IndexJobModel(Base):
    __tablename__ = "index_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    requested_profile: Mapped[str | None] = mapped_column(String(64))
    effective_profile: Mapped[str | None] = mapped_column(String(64))
    requested_parser: Mapped[str | None] = mapped_column(String(64))
    effective_parser: Mapped[str | None] = mapped_column(String(64))
    overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    vector_status: Mapped[str | None] = mapped_column(String(32))
    vector_error_message: Mapped[str | None] = mapped_column(Text)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndexNodeModel(Base):
    __tablename__ = "index_nodes"
    __table_args__ = (
        Index("ix_index_nodes_source_content_type", "source_id", "content_type"),
        Index("ix_index_nodes_notebook_profile", "notebook_id", "indexing_profile"),
    )

    node_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("index_jobs.job_id", ondelete="CASCADE"),
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    notebook_id: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    modality: Mapped[str] = mapped_column(String(32), index=True)
    content_type: Mapped[str] = mapped_column(String(64), index=True)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    block_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    parent_node_id: Mapped[str | None] = mapped_column(String(160), index=True)
    asset_path: Mapped[str | None] = mapped_column(String(1024))
    bbox: Mapped[list[float] | None] = mapped_column(JSON)
    indexing_profile: Mapped[str | None] = mapped_column(String(64), index=True)
    parser_version: Mapped[str | None] = mapped_column(String(64))
    chunker_version: Mapped[str | None] = mapped_column(String(64))
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    node_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
