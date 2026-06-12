"""
Tests for chunk quality metrics calculation.
"""

import pytest

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName, NodeGraphMode
from ragmax.domain.indexing.quality import (
    QualityThresholds,
    calculate_chunk_quality,
)


def test_empty_nodes_returns_empty_metrics():
    """Test that empty node list returns appropriate metrics."""
    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=(), blocks=(), profile=profile)

    assert metrics.avg_chunk_length == 0
    assert metrics.orphan_chunk_count == 0
    assert len(metrics.warnings) > 0
    assert "No nodes" in metrics.warnings[0]


def test_min_chunk_ratio_calculation():
    """Test calculation of small chunk ratio."""
    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="Short",  # 5 chars
            modality="text",
            content_type="paragraph",
            block_ids=("b1",),
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text="A" * 200,  # 200 chars
            modality="text",
            content_type="paragraph",
            block_ids=("b2",),
        ),
        IndexNode(
            node_id="n3",
            source_id="s1",
            notebook_id="nb1",
            text="Medium length text here",  # ~23 chars
            modality="text",
            content_type="paragraph",
            block_ids=("b3",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    # 2 out of 3 nodes are < 100 chars
    assert metrics.min_chunk_ratio == pytest.approx(2 / 3, rel=0.01)
    assert any("66.7%" in w for w in metrics.warnings)


def test_overlap_effectiveness_no_overlap():
    """Test overlap effectiveness when chunks don't overlap."""
    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="First chunk with unique content.",
            modality="text",
            content_type="paragraph",
            section_path=("Section 1",),
            block_ids=("b1",),
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text="Second chunk with completely different content.",
            modality="text",
            content_type="paragraph",
            section_path=("Section 1",),
            block_ids=("b2",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    # No actual overlap
    assert metrics.overlap_effectiveness < 0.1
    assert metrics.consecutive_overlap_pairs == 1
    assert any("Overlap effectiveness" in w for w in metrics.warnings)


def test_overlap_effectiveness_with_overlap():
    """Test overlap effectiveness when chunks have actual overlap."""
    overlap_text = " with overlapping content"

    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="First chunk" + overlap_text,
            modality="text",
            content_type="paragraph",
            section_path=("Section 1",),
            block_ids=("b1",),
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text=overlap_text + " and second chunk",
            modality="text",
            content_type="paragraph",
            section_path=("Section 1",),
            block_ids=("b2",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=25,  # Actual overlap is ~26 chars
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    # Should have good overlap effectiveness (26/25 = 1.0 capped)
    assert metrics.overlap_effectiveness > 0.9
    assert metrics.consecutive_overlap_pairs == 1


def test_section_coverage():
    """Test section coverage calculation."""
    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="Has section",
            modality="text",
            content_type="paragraph",
            section_path=("Section 1",),
            block_ids=("b1",),
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text="No section",
            modality="text",
            content_type="paragraph",
            section_path=(),  # Orphan
            block_ids=("b2",),
        ),
        IndexNode(
            node_id="n3",
            source_id="s1",
            notebook_id="nb1",
            text="Has section",
            modality="text",
            content_type="paragraph",
            section_path=("Section 2",),
            block_ids=("b3",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    assert metrics.orphan_chunk_count == 1
    assert metrics.section_coverage == pytest.approx(2 / 3, rel=0.01)


def test_table_integrity_no_split():
    """Test table integrity when tables are not split."""
    blocks = (
        ContentBlock(
            block_id="b1",
            source_id="s1",
            block_type=BlockType.TABLE,
            text="| A | B |\n|---|---|\n| 1 | 2 |",
        ),
        ContentBlock(
            block_id="b2",
            source_id="s1",
            block_type=BlockType.TEXT,
            text="Regular text",
        ),
    )

    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="| A | B |",
            modality="text",
            content_type="table",
            block_ids=("b1",),  # Table referenced by 1 node only
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text="Regular text",
            modality="text",
            content_type="paragraph",
            block_ids=("b2",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=blocks, profile=profile)

    assert metrics.table_integrity_score == 1.0
    assert metrics.split_table_count == 0


def test_table_integrity_with_split():
    """Test table integrity when a table is split across multiple nodes."""
    blocks = (
        ContentBlock(
            block_id="b1",
            source_id="s1",
            block_type=BlockType.TABLE,
            text="Large table",
        ),
    )

    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="Table part 1",
            modality="text",
            content_type="table",
            block_ids=("b1",),  # Same table referenced by multiple nodes
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text="Table part 2",
            modality="text",
            content_type="table",
            block_ids=("b1",),  # Split!
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=blocks, profile=profile)

    assert metrics.table_integrity_score == 0.0  # 1 table, 1 split = 0% integrity
    assert metrics.split_table_count == 1
    assert any("table" in w.lower() for w in metrics.warnings)


def test_parent_child_ratio():
    """Test parent-child ratio calculation in PARENT_CHILD mode."""
    nodes = (
        IndexNode(
            node_id="parent1",
            source_id="s1",
            notebook_id="nb1",
            text="Parent section",
            modality="text",
            content_type="section",
            block_ids=("b1",),
        ),
        IndexNode(
            node_id="child1",
            source_id="s1",
            notebook_id="nb1",
            text="Child 1",
            modality="text",
            content_type="paragraph",
            parent_node_id="parent1",
            block_ids=("b2",),
        ),
        IndexNode(
            node_id="child2",
            source_id="s1",
            notebook_id="nb1",
            text="Child 2",
            modality="text",
            content_type="paragraph",
            parent_node_id="parent1",
            block_ids=("b3",),
        ),
        IndexNode(
            node_id="child3",
            source_id="s1",
            notebook_id="nb1",
            text="Child 3",
            modality="text",
            content_type="paragraph",
            parent_node_id="parent1",
            block_ids=("b4",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.SECTION_AWARE,
        description="Test",
        chunker="section_aware",
        chunk_size=500,
        chunk_overlap=50,
        node_graph_mode=NodeGraphMode.PARENT_CHILD,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    assert metrics.parent_child_ratio == 3.0  # 3 children / 1 parent
    assert metrics.orphan_child_count == 0


def test_orphan_child_detection():
    """Test detection of children with invalid parent_node_id."""
    nodes = (
        IndexNode(
            node_id="child1",
            source_id="s1",
            notebook_id="nb1",
            text="Orphan child",
            modality="text",
            content_type="paragraph",
            parent_node_id="nonexistent_parent",  # Invalid!
            block_ids=("b1",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.SECTION_AWARE,
        description="Test",
        chunker="section_aware",
        chunk_size=500,
        chunk_overlap=50,
        node_graph_mode=NodeGraphMode.PARENT_CHILD,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    assert metrics.orphan_child_count == 1
    assert any("invalid parent_node_id" in w for w in metrics.warnings)


def test_bbox_coverage():
    """Test bbox coverage calculation."""
    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="Has bbox",
            modality="text",
            content_type="paragraph",
            bbox=(100, 200, 300, 250),
            block_ids=("b1",),
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text="No bbox",
            modality="text",
            content_type="paragraph",
            bbox=None,
            block_ids=("b2",),
        ),
        IndexNode(
            node_id="n3",
            source_id="s1",
            notebook_id="nb1",
            text="Has bbox",
            modality="text",
            content_type="paragraph",
            bbox=(100, 260, 300, 310),
            block_ids=("b3",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    assert metrics.bbox_coverage == pytest.approx(2 / 3, rel=0.01)


def test_avg_blocks_per_node():
    """Test average blocks per node calculation."""
    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="Single block",
            modality="text",
            content_type="paragraph",
            block_ids=("b1",),  # 1 block
        ),
        IndexNode(
            node_id="n2",
            source_id="s1",
            notebook_id="nb1",
            text="Multiple blocks",
            modality="text",
            content_type="paragraph",
            block_ids=("b2", "b3", "b4"),  # 3 blocks
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    metrics = calculate_chunk_quality(nodes=nodes, blocks=(), profile=profile)

    assert metrics.avg_blocks_per_node == 2.0  # (1 + 3) / 2
    assert metrics.single_block_node_ratio == 0.5  # 1 out of 2


def test_quality_thresholds_customization():
    """Test that custom thresholds affect warnings."""
    nodes = (
        IndexNode(
            node_id="n1",
            source_id="s1",
            notebook_id="nb1",
            text="A" * 150,  # 150 chars
            modality="text",
            content_type="paragraph",
            block_ids=("b1",),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
    )

    # With strict threshold
    strict_thresholds = QualityThresholds(min_chunk_length=200)
    metrics_strict = calculate_chunk_quality(
        nodes=nodes, blocks=(), profile=profile, thresholds=strict_thresholds
    )

    # With lenient threshold
    lenient_thresholds = QualityThresholds(min_chunk_length=100)
    metrics_lenient = calculate_chunk_quality(
        nodes=nodes, blocks=(), profile=profile, thresholds=lenient_thresholds
    )

    # Strict should have warning, lenient should not
    assert len(metrics_strict.warnings) > len(metrics_lenient.warnings)
