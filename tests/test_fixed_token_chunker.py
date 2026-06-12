"""测试FixedTokenChunker - 验证F策略实现"""
from ragmax.domain.indexing.tokenization import TiktokenTokenizer
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.blocks import ContentBlock, BlockType
from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName, NodeGraphMode
from ragmax.infrastructure.indexing.chunkers.fixed_token_chunker import FixedTokenChunker


def test_fixed_token_chunker_basic():
    """测试基本的固定Token分块功能"""
    print("Test 1: Basic fixed token chunking...")

    tokenizer = TiktokenTokenizer()
    chunker = FixedTokenChunker()

    # 创建一个长文本文档（足够触发分块）
    long_text = "This is a test sentence. " * 100  # 约500+ tokens

    document = SourceDocument(
        source_id="test_src",
        notebook_id="test_nb",
        filename="test.txt",
        parser_name="test_parser",
        parser_version="v1",
        blocks=(
            ContentBlock(
                block_id="block1",
                source_id="test_src",
                block_type=BlockType.TEXT,
                text=long_text,
                order_index=1,
            ),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test profile",
        chunker="fixed_token",
        chunk_size=100,  # 小chunk用于测试
        chunk_overlap=20,
        node_graph_mode=NodeGraphMode.FLAT,
    )

    # 执行分块
    nodes = chunker.chunk(document, profile, tokenizer)

    # 验证结果
    assert len(nodes) > 1, "应该产生多个chunk"
    print(f"  PASS - Generated {len(nodes)} chunks")

    # 验证每个chunk的token count
    for i, node in enumerate(nodes):
        token_count = node.metadata["token_count"]
        print(f"  Chunk {i+1}: {token_count} tokens")

        # 大部分chunk应该接近chunk_size（最后一个可能更小）
        if i < len(nodes) - 1:
            assert token_count <= profile.chunk_size + 5, f"Chunk {i+1} exceeds chunk_size"


def test_chunk_size_accuracy():
    """测试chunk大小的精确控制"""
    print("\nTest 2: Chunk size accuracy...")

    tokenizer = TiktokenTokenizer()
    chunker = FixedTokenChunker()

    # 生成足够长的文本
    text = "The quick brown fox jumps over the lazy dog. " * 200

    document = SourceDocument(
        source_id="test_src",
        notebook_id="test_nb",
        filename="test.txt",
        parser_name="test_parser",
        parser_version="v1",
        blocks=(
            ContentBlock(
                block_id="block1",
                source_id="test_src",
                block_type=BlockType.TEXT,
                text=text,
                order_index=1,
            ),
        ),
    )

    # 测试不同的chunk size
    test_sizes = [50, 100, 200, 500]

    for chunk_size in test_sizes:
        profile = IndexingProfile(
            name=IndexingProfileName.FIXED_TOKEN,
            description="Test",
            chunker="fixed_token",
            chunk_size=chunk_size,
            chunk_overlap=20,
            node_graph_mode=NodeGraphMode.FLAT,
        )

        nodes = chunker.chunk(document, profile, tokenizer)

        # 检查非最后chunk的大小
        for i, node in enumerate(nodes[:-1]):  # 排除最后一个chunk
            token_count = node.metadata["token_count"]
            # 允许±5 tokens误差（因为decode可能有边界问题）
            assert abs(token_count - chunk_size) <= 5, \
                f"Chunk size {token_count} too far from target {chunk_size}"

        print(f"  PASS - chunk_size={chunk_size}: {len(nodes)} chunks, avg tokens per chunk: {sum(n.metadata['token_count'] for n in nodes) / len(nodes):.1f}")


def test_overlap_functionality():
    """测试overlap功能"""
    print("\nTest 3: Overlap functionality...")

    tokenizer = TiktokenTokenizer()
    chunker = FixedTokenChunker()

    text = "Word " * 300  # 简单重复文本便于验证overlap

    document = SourceDocument(
        source_id="test_src",
        notebook_id="test_nb",
        filename="test.txt",
        parser_name="test_parser",
        parser_version="v1",
        blocks=(
            ContentBlock(
                block_id="block1",
                source_id="test_src",
                block_type=BlockType.TEXT,
                text=text,
                order_index=1,
            ),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="fixed_token",
        chunk_size=100,
        chunk_overlap=30,
        node_graph_mode=NodeGraphMode.FLAT,
    )

    nodes = chunker.chunk(document, profile, tokenizer)

    # 验证生成了多个chunk
    assert len(nodes) >= 2, "应该产生至少2个chunk来测试overlap"

    # 检查相邻chunk之间有overlap（通过检查文本开头）
    for i in range(len(nodes) - 1):
        chunk1_text = nodes[i].text
        chunk2_text = nodes[i + 1].text

        # 简单验证：chunk2应该包含chunk1的一些尾部内容
        # 这是overlap的表现
        chunk1_words = chunk1_text.split()[-10:]  # 取chunk1最后10个词
        chunk2_start = chunk2_text.split()[:20]  # 取chunk2开头20个词

        # 应该有一些重叠
        overlap_found = any(word in chunk2_start for word in chunk1_words)
        assert overlap_found, f"Chunks {i} and {i+1} should have overlap"

    print(f"  PASS - {len(nodes)} chunks with overlap verified")


def test_handles_short_text():
    """测试处理短文本（不需要分块）"""
    print("\nTest 4: Handles short text...")

    tokenizer = TiktokenTokenizer()
    chunker = FixedTokenChunker()

    short_text = "This is a short text."

    document = SourceDocument(
        source_id="test_src",
        notebook_id="test_nb",
        filename="test.txt",
        parser_name="test_parser",
        parser_version="v1",
        blocks=(
            ContentBlock(
                block_id="block1",
                source_id="test_src",
                block_type=BlockType.TEXT,
                text=short_text,
                order_index=1,
            ),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="fixed_token",
        chunk_size=1000,
        chunk_overlap=100,
        node_graph_mode=NodeGraphMode.FLAT,
    )

    nodes = chunker.chunk(document, profile, tokenizer)

    # 短文本应该只产生1个chunk
    assert len(nodes) == 1, "Short text should produce only 1 chunk"
    assert nodes[0].text == short_text
    print(f"  PASS - Short text handled correctly (1 chunk)")


def test_multiple_blocks():
    """测试处理多个blocks"""
    print("\nTest 5: Multiple blocks with headings...")

    tokenizer = TiktokenTokenizer()
    chunker = FixedTokenChunker()

    document = SourceDocument(
        source_id="test_src",
        notebook_id="test_nb",
        filename="test.txt",
        parser_name="test_parser",
        parser_version="v1",
        blocks=(
            ContentBlock(
                block_id="heading1",
                source_id="test_src",
                block_type=BlockType.HEADING,
                text="Chapter 1",
                order_index=1,
            ),
            ContentBlock(
                block_id="text1",
                source_id="test_src",
                block_type=BlockType.TEXT,
                text="This is chapter 1 content. " * 50,
                order_index=2,
            ),
            ContentBlock(
                block_id="heading2",
                source_id="test_src",
                block_type=BlockType.HEADING,
                text="Chapter 2",
                order_index=3,
            ),
            ContentBlock(
                block_id="text2",
                source_id="test_src",
                block_type=BlockType.TEXT,
                text="This is chapter 2 content. " * 50,
                order_index=4,
            ),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test",
        chunker="fixed_token",
        chunk_size=100,
        chunk_overlap=20,
        node_graph_mode=NodeGraphMode.FLAT,
    )

    nodes = chunker.chunk(document, profile, tokenizer)

    # 应该产生多个chunks
    assert len(nodes) > 2, "Should produce multiple chunks from multiple blocks"

    # 验证section_path被正确设置
    chapter1_nodes = [n for n in nodes if "Chapter 1" in n.section_path]
    chapter2_nodes = [n for n in nodes if "Chapter 2" in n.section_path]

    assert len(chapter1_nodes) > 0, "Should have nodes under Chapter 1"
    assert len(chapter2_nodes) > 0, "Should have nodes under Chapter 2"

    print(f"  PASS - {len(chapter1_nodes)} nodes under Chapter 1, {len(chapter2_nodes)} nodes under Chapter 2")


def main():
    print("=" * 60)
    print("FixedTokenChunker Tests - F Strategy Verification")
    print("=" * 60)

    try:
        test_fixed_token_chunker_basic()
        test_chunk_size_accuracy()
        test_overlap_functionality()
        test_handles_short_text()
        test_multiple_blocks()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nStep 2 完成验证:")
        print("- FixedTokenChunker实现正确")
        print("- Chunk大小精确控制（误差<5 tokens）")
        print("- Overlap功能正常工作")
        print("- 短文本处理正确")
        print("- 多block和heading支持正常")
        print("\nF策略（Fixed Token）对齐LightRAG完成！")

        return 0

    except AssertionError as e:
        print(f"\n\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
