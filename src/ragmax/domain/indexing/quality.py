"""
Chunk quality metrics and analysis.

This module provides comprehensive quality assessment for chunked documents,
enabling data-driven optimization of indexing strategies.
"""

from dataclasses import dataclass, field
from typing import Any

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.entities import IndexNode


@dataclass(frozen=True)
class ChunkQualityMetrics:
    """Comprehensive chunk quality metrics."""

    # 1. Basic quality indicators
    min_chunk_ratio: float
    """Ratio of chunks < 100 chars (0-1), target <0.05"""

    avg_chunk_length: int
    """Average chunk length in characters"""

    chunk_length_std: float
    """Standard deviation of chunk lengths"""

    # 2. Overlap effectiveness
    overlap_effectiveness: float
    """Actual overlap coverage (0-1), target >0.8

    Measures how well the configured overlap is actually applied.
    Low values (<0.5) indicate sentence splitter issues.
    """

    consecutive_overlap_pairs: int
    """Number of adjacent chunk pairs with overlap"""

    # 3. Structural integrity
    orphan_chunk_count: int
    """Number of chunks without section_path, target =0"""

    section_coverage: float
    """Ratio of nodes with section_path (0-1), target >0.9"""

    section_balance_std: float
    """Standard deviation of section sizes

    High values (>0.5) indicate imbalanced sections:
    - Some sections too long (possible heading detection error)
    - Some sections too short (possible over-splitting)
    """

    # 4. Table integrity
    table_integrity_score: float
    """Ratio of non-split tables (0-1), target >0.9"""

    split_table_count: int
    """Number of tables that were split"""

    # 5. Block reuse rate
    avg_blocks_per_node: float
    """Average blocks per node

    Too low (<1.5): over-splitting
    Too high (>10): under-splitting
    Target: 2-5
    """

    single_block_node_ratio: float
    """Ratio of nodes with only one block"""

    # 6. Parent-child quality
    parent_child_ratio: float | None
    """Child/parent ratio (only in PARENT_CHILD mode)

    Target: 2-10
    Too low (<1): too many parents
    Too high (>20): children explosion
    """

    orphan_child_count: int
    """Number of children with invalid parent_node_id, target =0"""

    # 7. Bbox coverage
    bbox_coverage: float
    """Ratio of nodes with bbox (0-1), target >0.95"""

    # 8. Automatic warnings
    warnings: list[str] = field(default_factory=list)
    """Auto-generated warnings based on thresholds"""

    quality_version: str = "v1.0"
    """Quality metrics version for backward compatibility"""


@dataclass(frozen=True)
class QualityThresholds:
    """Quality thresholds for generating warnings."""

    min_chunk_length: int = 100
    max_chunk_length: int = 2000
    min_overlap_effectiveness: float = 0.6
    max_orphan_ratio: float = 0.05
    min_section_coverage: float = 0.8
    max_section_balance_std: float = 0.6
    min_table_integrity: float = 0.85
    min_bbox_coverage: float = 0.9


def calculate_chunk_quality(
    nodes: tuple[IndexNode, ...],
    blocks: tuple[ContentBlock, ...],
    chunk_config: dict[str, Any],
    thresholds: QualityThresholds | None = None,
) -> ChunkQualityMetrics:
    """
    Calculate comprehensive chunk quality metrics.

    Args:
        nodes: All IndexNodes
        blocks: Original ContentBlocks (for block reuse calculation)
        chunk_config: Chunking configuration dict
        thresholds: Warning thresholds configuration

    Returns:
        ChunkQualityMetrics with all calculated indicators
    """
    if not nodes:
        return _empty_metrics()

    thresholds = thresholds or QualityThresholds()
    warnings: list[str] = []

    # Extract config values
    chunk_size = chunk_config.get("chunk_size", 1000)
    chunk_overlap = chunk_config.get("chunk_overlap", 100)

    # 1. Basic length statistics
    lengths = [len(node.text) for node in nodes]
    min_chunk_ratio = sum(1 for l in lengths if l < thresholds.min_chunk_length) / len(lengths)
    avg_chunk_length = sum(lengths) // len(lengths)
    chunk_length_std = _std_deviation(lengths)

    if min_chunk_ratio > 0.1:
        warnings.append(
            f"⚠️ {min_chunk_ratio*100:.1f}% chunks < {thresholds.min_chunk_length} chars, "
            f"consider increasing chunk_size (current: {chunk_size})"
        )

    # 2. Overlap effectiveness
    overlap_stats = _calculate_overlap_effectiveness(nodes, chunk_overlap)
    if overlap_stats["effectiveness"] < thresholds.min_overlap_effectiveness:
        warnings.append(
            f"⚠️ Overlap effectiveness only {overlap_stats['effectiveness']*100:.0f}%, "
            f"configured {chunk_overlap} chars overlap not fully effective"
        )

    # 3. Section integrity
    orphan_count = sum(1 for node in nodes if not node.section_path)
    section_coverage = 1 - (orphan_count / len(nodes))

    if section_coverage < thresholds.min_section_coverage:
        warnings.append(
            f"⚠️ {orphan_count} nodes lack section_path, "
            f"check parser's section_hint extraction"
        )

    # Section balance
    section_sizes = _group_by_section(nodes)
    section_balance_std = (
        _std_deviation(list(section_sizes.values())) if section_sizes else 0.0
    )

    # 4. Table integrity
    table_stats = _analyze_table_integrity(nodes, blocks)
    if table_stats["split_count"] > 0:
        warnings.append(
            f"⚠️ {table_stats['split_count']} tables were split, "
            f"integrity score: {table_stats['score']*100:.0f}%"
        )

    # 5. Block reuse rate
    total_block_refs = sum(len(node.block_ids) for node in nodes)
    avg_blocks_per_node = total_block_refs / len(nodes)
    single_block_ratio = sum(1 for node in nodes if len(node.block_ids) == 1) / len(nodes)

    # 6. Parent-child quality
    parent_child_stats = _analyze_parent_child_structure(
        nodes,
        node_graph_mode=str(chunk_config.get("node_graph_mode") or "flat"),
    )
    if parent_child_stats["orphan_child_count"] > 0:
        warnings.append(
            f"❌ {parent_child_stats['orphan_child_count']} child nodes have invalid parent_node_id"
        )

    # 7. Bbox coverage
    bbox_coverage = sum(1 for node in nodes if node.bbox is not None) / len(nodes)
    if bbox_coverage < thresholds.min_bbox_coverage:
        warnings.append(
            f"⚠️ Only {bbox_coverage*100:.0f}% nodes have bbox, "
            f"check parser's bbox extraction"
        )

    return ChunkQualityMetrics(
        min_chunk_ratio=min_chunk_ratio,
        avg_chunk_length=avg_chunk_length,
        chunk_length_std=chunk_length_std,
        overlap_effectiveness=overlap_stats["effectiveness"],
        consecutive_overlap_pairs=overlap_stats["overlap_pairs"],
        orphan_chunk_count=orphan_count,
        section_coverage=section_coverage,
        section_balance_std=section_balance_std,
        table_integrity_score=table_stats["score"],
        split_table_count=table_stats["split_count"],
        avg_blocks_per_node=avg_blocks_per_node,
        single_block_node_ratio=single_block_ratio,
        parent_child_ratio=parent_child_stats["ratio"],
        orphan_child_count=parent_child_stats["orphan_child_count"],
        bbox_coverage=bbox_coverage,
        warnings=warnings,
    )


def _empty_metrics() -> ChunkQualityMetrics:
    """Return empty metrics when no nodes available."""
    return ChunkQualityMetrics(
        min_chunk_ratio=0.0,
        avg_chunk_length=0,
        chunk_length_std=0.0,
        overlap_effectiveness=1.0,
        consecutive_overlap_pairs=0,
        orphan_chunk_count=0,
        section_coverage=1.0,
        section_balance_std=0.0,
        table_integrity_score=1.0,
        split_table_count=0,
        avg_blocks_per_node=0.0,
        single_block_node_ratio=0.0,
        parent_child_ratio=None,
        orphan_child_count=0,
        bbox_coverage=0.0,
        warnings=["⚠️ No nodes to analyze"],
    )


def _calculate_overlap_effectiveness(
    nodes: tuple[IndexNode, ...],
    configured_overlap: int,
) -> dict:
    """
    Calculate overlap effectiveness.

    Theoretical overlap: adjacent chunks should have configured_overlap chars overlap
    Actual overlap: calculated by text comparison
    """
    if len(nodes) < 2:
        return {"effectiveness": 1.0, "overlap_pairs": 0}

    # Group consecutive nodes by section (only same-section adjacent chunks should overlap)
    grouped = _group_consecutive_nodes_by_section(nodes)

    total_expected_overlap = 0
    total_actual_overlap = 0
    overlap_pairs = 0

    for section_nodes in grouped.values():
        for i in range(len(section_nodes) - 1):
            node1 = section_nodes[i]
            node2 = section_nodes[i + 1]

            # Calculate actual overlap characters
            actual_overlap = _count_text_overlap(node1.text, node2.text)

            total_expected_overlap += configured_overlap
            total_actual_overlap += actual_overlap
            overlap_pairs += 1

    if total_expected_overlap == 0:
        return {"effectiveness": 1.0, "overlap_pairs": 0}

    effectiveness = min(1.0, total_actual_overlap / total_expected_overlap)
    return {"effectiveness": effectiveness, "overlap_pairs": overlap_pairs}


def _count_text_overlap(text1: str, text2: str) -> int:
    """Count actual overlapping characters (from text1 end and text2 start)."""
    max_overlap = min(len(text1), len(text2), 500)  # Limit search range

    for overlap_len in range(max_overlap, 0, -1):
        suffix = text1[-overlap_len:]
        prefix = text2[:overlap_len]
        if suffix == prefix:
            return overlap_len

    return 0


def _analyze_table_integrity(
    nodes: tuple[IndexNode, ...],
    blocks: tuple[ContentBlock, ...],
) -> dict:
    """
    Analyze table integrity.

    Logic:
    1. Find all TABLE type blocks
    2. For each table block, count how many nodes reference it
    3. If >1 nodes reference the same table block, count as "split"
    """
    table_blocks = {b.block_id for b in blocks if b.block_type == BlockType.TABLE}

    if not table_blocks:
        return {"score": 1.0, "split_count": 0, "total_tables": 0}

    # Count how many nodes reference each table block
    table_ref_count: dict[str, int] = {tb: 0 for tb in table_blocks}
    for node in nodes:
        for block_id in node.block_ids:
            if block_id in table_blocks:
                table_ref_count[block_id] += 1

    split_tables = sum(1 for count in table_ref_count.values() if count > 1)
    total_tables = len(table_blocks)
    integrity_score = 1 - (split_tables / total_tables)

    return {
        "score": integrity_score,
        "split_count": split_tables,
        "total_tables": total_tables,
    }


def _analyze_parent_child_structure(
    nodes: tuple[IndexNode, ...],
    node_graph_mode: str,
) -> dict:
    """Analyze parent-child structure quality."""
    if node_graph_mode != "parent_child":
        return {"ratio": None, "orphan_child_count": 0}

    parent_ids = {node.node_id for node in nodes if node.content_type == "section"}
    child_nodes = [node for node in nodes if node.parent_node_id]

    orphan_children = sum(1 for node in child_nodes if node.parent_node_id not in parent_ids)

    parent_count = len(parent_ids)
    child_count = len(child_nodes)
    ratio = child_count / parent_count if parent_count > 0 else None

    return {
        "ratio": ratio,
        "orphan_child_count": orphan_children,
    }


def _std_deviation(values: list[int | float]) -> float:
    """Calculate standard deviation."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance**0.5


def _group_by_section(nodes: tuple[IndexNode, ...]) -> dict[tuple[str, ...], int]:
    """Group by section_path, return node count per section."""
    from collections import defaultdict

    section_sizes = defaultdict(int)
    for node in nodes:
        section_sizes[node.section_path] += 1
    return dict(section_sizes)


def _group_consecutive_nodes_by_section(nodes: tuple[IndexNode, ...]) -> dict:
    """Group nodes by section, maintaining order."""
    from collections import defaultdict

    grouped = defaultdict(list)
    for node in nodes:
        grouped[node.section_path].append(node)
    return grouped
