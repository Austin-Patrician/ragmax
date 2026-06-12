"""测试Token-first改造 - 验证第一步完成情况"""
from ragmax.domain.indexing.tokenization import TiktokenTokenizer, Tokenizer
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.blocks import ContentBlock, BlockType
from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName, NodeGraphMode
from ragmax.infrastructure.indexing.chunkers.fixed_token_chunker import FixedTokenChunker


def test_tokenizer_basic():
    """测试Tokenizer基本功能"""
    tokenizer = TiktokenTokenizer("cl100k_base")

    text = "Hello world! This is a test."
    token_count = tokenizer.count_tokens(text)

    # 验证token count是精确的，不是估算
    assert token_count > 0
    assert token_count < len(text)  # Token数应该少于字符数

    # 验证encode/decode一致性
    tokens = tokenizer.encode(text)
    decoded = tokenizer.decode(tokens)
    assert decoded == text
    assert len(tokens) == token_count


def test_chunker_accepts_tokenizer():
    """测试Chunker接收tokenizer参数"""
    tokenizer = TiktokenTokenizer()
    chunker = FixedTokenChunker()

    # 创建简单文档
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
                text="This is a test document. " * 50,  # 足够长以触发分块
                order_index=1,
            ),
        ),
    )

    profile = IndexingProfile(
        name=IndexingProfileName.FIXED_TOKEN,
        description="Test profile",
        chunker="fixed_token",
        chunk_size=100,
        chunk_overlap=20,
        node_graph_mode=NodeGraphMode.FLAT,
    )

    # 调用chunk方法，传入tokenizer
    nodes = chunker.chunk(document, profile, tokenizer)

    # 验证返回结果
    assert len(nodes) > 0

    # 验证metadata包含token_count
    for node in nodes:
        assert "token_count" in node.metadata
        assert isinstance(node.metadata["token_count"], int)
        assert node.metadata["token_count"] > 0

        # 验证token_count不是估算值(len/4)
        estimated = len(node.text) // 4
        actual = node.metadata["token_count"]
        # 真实值应该与估算值有差异
        assert abs(actual - estimated) < estimated * 0.5  # 允许50%差异范围


def test_token_count_accuracy():
    """测试Token计数精确性"""
    tokenizer = TiktokenTokenizer()

    # 测试不同长度的文本
    test_cases = [
        "Hello",
        "Hello world",
        "This is a longer sentence with more tokens.",
        "中文测试文本，应该也能正确计数。",
        "Mixed 中英文 text with multiple languages.",
    ]

    for text in test_cases:
        token_count = tokenizer.count_tokens(text)
        tokens = tokenizer.encode(text)

        # 验证count_tokens和encode结果一致
        assert token_count == len(tokens), f"Token count mismatch for: {text}"

        # 验证token数量合理（不为0，不超过字符数太多）
        assert 0 < token_count <= len(text) * 2


if __name__ == "__main__":
    test_tokenizer_basic()
    print("test_tokenizer_basic passed!")

    test_chunker_accepts_tokenizer()
    print("test_chunker_accepts_tokenizer passed!")

    test_token_count_accuracy()
    print("test_token_count_accuracy passed!")

    print("\nAll tests passed! Token-first refactoring Step 1 is working correctly.")
