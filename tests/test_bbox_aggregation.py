"""
Tests for bbox aggregation strategies.
"""

import pytest

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


@pytest.fixture
def chunker():
    """Create a BaseChunker instance for testing."""
    return BaseChunker()


@pytest.fixture
def profile_union():
    """Profile with union bbox strategy."""
    return IndexingProfile(
        name=IndexingProfileName.DEFAULT_PDF,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
        options={"bbox_aggregation_strategy": "union"},
    )


@pytest.fixture
def profile_first():
    """Profile with first bbox strategy."""
    return IndexingProfile(
        name=IndexingProfileName.DEFAULT_PDF,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
        options={"bbox_aggregation_strategy": "first"},
    )


@pytest.fixture
def document():
    """Create a test document."""
    return SourceDocument(
        source_id="test-source",
        notebook_id="test-notebook",
        filename="test.pdf",
        media_type="application/pdf",
        parser_name="test_parser",
        parser_version="v1",
        blocks=(),
    )


def test_no_bbox_returns_none(chunker, profile_union, document):
    """Test that blocks without bbox return None."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="No bbox",
            bbox=None,
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_union,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    assert node.bbox is None


def test_single_bbox_returns_as_is(chunker, profile_union, document):
    """Test that single bbox is returned unchanged."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Has bbox",
            bbox=(100.0, 200.0, 300.0, 250.0),
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_union,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    assert node.bbox == (100.0, 200.0, 300.0, 250.0)


def test_union_strategy_computes_bounding_box(chunker, profile_union, document):
    """Test that union strategy computes minimum bounding box."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 1",
            bbox=(100.0, 200.0, 300.0, 250.0),  # Top block
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 2",
            bbox=(100.0, 260.0, 300.0, 310.0),  # Middle block
        ),
        ContentBlock(
            block_id="b3",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 3",
            bbox=(100.0, 320.0, 300.0, 370.0),  # Bottom block
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_union,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Union should encompass all blocks
    assert node.bbox == (100.0, 200.0, 300.0, 370.0)


def test_union_strategy_handles_scattered_blocks(chunker, profile_union, document):
    """Test union with blocks at different x positions (e.g., columns)."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Left column",
            bbox=(50.0, 100.0, 250.0, 150.0),  # Left
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Right column",
            bbox=(300.0, 100.0, 500.0, 150.0),  # Right
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_union,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Union should span both columns
    assert node.bbox == (50.0, 100.0, 500.0, 150.0)


def test_first_strategy_takes_first_bbox(chunker, profile_first, document):
    """Test that first strategy takes only the first bbox."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 1",
            bbox=(100.0, 200.0, 300.0, 250.0),  # First
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 2",
            bbox=(100.0, 260.0, 300.0, 310.0),  # Ignored
        ),
        ContentBlock(
            block_id="b3",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 3",
            bbox=(100.0, 320.0, 300.0, 370.0),  # Ignored
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_first,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Should only use first bbox
    assert node.bbox == (100.0, 200.0, 300.0, 250.0)


def test_union_strategy_skips_none_bboxes(chunker, profile_union, document):
    """Test that union strategy ignores blocks without bbox."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="No bbox",
            bbox=None,  # Skipped
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Has bbox 1",
            bbox=(100.0, 200.0, 300.0, 250.0),
        ),
        ContentBlock(
            block_id="b3",
            source_id="test",
            block_type=BlockType.TEXT,
            text="No bbox",
            bbox=None,  # Skipped
        ),
        ContentBlock(
            block_id="b4",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Has bbox 2",
            bbox=(100.0, 260.0, 300.0, 310.0),
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_union,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Should compute union of only the 2 valid bboxes
    assert node.bbox == (100.0, 200.0, 300.0, 310.0)


def test_first_strategy_skips_to_first_valid_bbox(chunker, profile_first, document):
    """Test that first strategy skips None bboxes to find first valid one."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="No bbox",
            bbox=None,  # Skipped
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="First valid",
            bbox=(100.0, 200.0, 300.0, 250.0),  # This one
        ),
        ContentBlock(
            block_id="b3",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Second valid",
            bbox=(100.0, 260.0, 300.0, 310.0),  # Ignored
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_first,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Should use first valid bbox (b2)
    assert node.bbox == (100.0, 200.0, 300.0, 250.0)


def test_default_strategy_is_union(chunker, document):
    """Test that default strategy (when not specified) is union."""
    profile_default = IndexingProfile(
        name=IndexingProfileName.DEFAULT_PDF,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
        # No bbox_aggregation_strategy specified
    )

    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 1",
            bbox=(100.0, 200.0, 300.0, 250.0),
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 2",
            bbox=(100.0, 260.0, 300.0, 310.0),
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_default,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Should default to union
    assert node.bbox == (100.0, 200.0, 300.0, 310.0)


def test_union_with_negative_coordinates(chunker, profile_union, document):
    """Test union with negative coordinates (some PDF coordinate systems)."""
    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 1",
            bbox=(-100.0, -200.0, 100.0, -150.0),
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 2",
            bbox=(-50.0, -140.0, 150.0, -100.0),
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_union,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Union should handle negative coords correctly
    assert node.bbox == (-100.0, -200.0, 150.0, -100.0)


def test_unknown_strategy_defaults_to_union(chunker, document):
    """Test that unknown strategy falls back to union."""
    profile_unknown = IndexingProfile(
        name=IndexingProfileName.DEFAULT_PDF,
        description="Test",
        chunker="test",
        chunk_size=500,
        chunk_overlap=50,
        options={"bbox_aggregation_strategy": "unknown_strategy"},
    )

    blocks = [
        ContentBlock(
            block_id="b1",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 1",
            bbox=(100.0, 200.0, 300.0, 250.0),
        ),
        ContentBlock(
            block_id="b2",
            source_id="test",
            block_type=BlockType.TEXT,
            text="Block 2",
            bbox=(100.0, 260.0, 300.0, 310.0),
        ),
    ]

    node = chunker._make_node(
        document=document,
        profile=profile_unknown,
        text="Test",
        content_type="paragraph",
        blocks=blocks,
    )

    # Should fallback to union
    assert node.bbox == (100.0, 200.0, 300.0, 310.0)
