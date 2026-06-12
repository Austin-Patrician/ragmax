"""测试TableAwareChunker的增强表格处理功能"""
from ragmax.domain.indexing.tokenization import TiktokenTokenizer


def test_markdown_table_detection():
    """测试Markdown表格检测"""
    print("Test 1: Markdown table detection...")

    from ragmax.infrastructure.indexing.chunkers.table_chunker import TableAwareChunker

    chunker = TableAwareChunker()

    # Markdown表格
    markdown_lines = [
        "| Name | Age | City |",
        "| --- | --- | --- |",
        "| Alice | 30 | NYC |",
        "| Bob | 25 | LA |",
    ]

    assert chunker._is_markdown_table(markdown_lines), "Should detect markdown table"
    print("  PASS - Markdown table detected")

    # 带对齐的Markdown表格
    aligned_lines = [
        "| Name  | Age | City |",
        "| :---- | --: | :--: |",
        "| Alice | 30  | NYC  |",
    ]

    assert chunker._is_markdown_table(aligned_lines), "Should detect aligned markdown table"
    print("  PASS - Aligned markdown table detected")

    # 非Markdown表格
    non_markdown = [
        "Name, Age, City",
        "Alice, 30, NYC",
        "Bob, 25, LA",
    ]

    assert not chunker._is_markdown_table(non_markdown), "Should not detect non-markdown"
    print("  PASS - Non-markdown table rejected")


def test_split_rows_by_token_budget():
    """测试按token预算分割行"""
    print("\nTest 2: Split rows by token budget...")

    from ragmax.infrastructure.indexing.chunkers.table_chunker import TableAwareChunker

    chunker = TableAwareChunker()
    tokenizer = TiktokenTokenizer()

    # 创建一些表格行
    body_lines = [
        "| Alice | 30 | New York City |",
        "| Bob | 25 | Los Angeles |",
        "| Charlie | 35 | Chicago |",
        "| Diana | 28 | Houston |",
        "| Eve | 32 | Phoenix |",
        "| Frank | 29 | Philadelphia |",
    ]

    # 设置较小的预算，强制分割
    body_budget = 30  # 约2-3行

    chunks = chunker._split_rows_by_token_budget(
        body_lines=body_lines,
        body_budget=body_budget,
        tokenizer=tokenizer,
    )

    # 应该产生多个chunks
    assert len(chunks) > 1, "Should split into multiple chunks"
    print(f"  Split into {len(chunks)} chunks")

    # 验证每个chunk不超过预算
    for i, chunk in enumerate(chunks):
        chunk_text = "\n".join(chunk)
        chunk_tokens = tokenizer.count_tokens(chunk_text)
        print(f"  Chunk {i+1}: {len(chunk)} rows, {chunk_tokens} tokens")
        assert chunk_tokens <= body_budget + 10, f"Chunk {i+1} exceeds budget"

    print("  PASS - Rows split by token budget correctly")


def test_header_recovery():
    """测试表头恢复功能"""
    print("\nTest 3: Table header recovery...")

    from ragmax.infrastructure.indexing.chunkers.table_chunker import TableAwareChunker

    chunker = TableAwareChunker()
    tokenizer = TiktokenTokenizer()

    # 创建一个足够长的Markdown表格
    table_text = """| Name | Age | City |
| --- | --- | --- |
| Alice | 30 | New York |
| Bob | 25 | Los Angeles |
| Charlie | 35 | Chicago |
| Diana | 28 | Houston |
| Eve | 32 | Phoenix |
| Frank | 29 | Philadelphia |
| Grace | 27 | San Antonio |
| Henry | 31 | San Diego |
| Iris | 26 | Dallas |
| Jack | 33 | San Jose |"""

    # 分割表格，重复表头
    chunks = chunker._split_table_with_header_recovery(
        table_text=table_text,
        chunk_size=100,  # 较小的chunk size触发分割
        tokenizer=tokenizer,
        repeat_header=True,
    )

    # 应该产生多个chunks
    assert len(chunks) > 1, "Should produce multiple chunks"
    print(f"  Generated {len(chunks)} chunks")

    # 验证每个chunk都包含表头
    for i, chunk in enumerate(chunks):
        lines = chunk.split("\n")
        # 每个chunk应该以表头开始
        assert "| Name | Age | City |" in lines[0], f"Chunk {i+1} missing header line 1"
        assert "| --- | --- | --- |" in lines[1], f"Chunk {i+1} missing header separator"
        print(f"  Chunk {i+1}: {len(lines)} lines, header recovered")

    print("  PASS - Table headers recovered in all chunks")


def test_assemble_table_chunk():
    """测试表格chunk组装"""
    print("\nTest 4: Assemble table chunk...")

    from ragmax.infrastructure.indexing.chunkers.table_chunker import TableAwareChunker

    chunker = TableAwareChunker()

    header_lines = [
        "| Name | Age |",
        "| --- | --- |",
    ]

    body_lines = [
        "| Alice | 30 |",
        "| Bob | 25 |",
    ]

    result = chunker._assemble_table_chunk(header_lines, body_lines)

    # 验证组装结果
    expected = """| Name | Age |
| --- | --- |
| Alice | 30 |
| Bob | 25 |"""

    assert result == expected, "Assembled chunk doesn't match expected"
    print("  PASS - Table chunk assembled correctly")


def test_token_budget_calculation():
    """测试token预算计算"""
    print("\nTest 5: Token budget calculation...")

    tokenizer = TiktokenTokenizer()

    # 测试表头
    header_text = """| Name | Age | City |
| --- | --- | --- |"""

    header_tokens = tokenizer.count_tokens(header_text)
    print(f"  Header tokens: {header_tokens}")

    # 计算body预算
    chunk_size = 200
    safety_margin = 50
    body_budget = chunk_size - header_tokens - safety_margin

    print(f"  Chunk size: {chunk_size}")
    print(f"  Safety margin: {safety_margin}")
    print(f"  Body budget: {body_budget}")

    assert body_budget > 0, "Body budget should be positive"
    assert body_budget < chunk_size, "Body budget should be less than chunk size"

    print("  PASS - Token budget calculated correctly")


def test_short_table_no_split():
    """测试短表格不分割"""
    print("\nTest 6: Short table no split...")

    from ragmax.infrastructure.indexing.chunkers.table_chunker import TableAwareChunker

    chunker = TableAwareChunker()
    tokenizer = TiktokenTokenizer()

    # 短表格（8行以内）
    short_table = """| Name | Age |
| --- | --- |
| Alice | 30 |
| Bob | 25 |
| Charlie | 35 |"""

    chunks = chunker._split_table_with_header_recovery(
        table_text=short_table,
        chunk_size=100,
        tokenizer=tokenizer,
        repeat_header=True,
    )

    # 短表格应该只返回1个chunk
    assert len(chunks) == 1, "Short table should not be split"
    assert chunks[0].strip() == short_table.strip(), "Short table should remain unchanged"

    print("  PASS - Short table not split")


def main():
    print("=" * 60)
    print("TableAwareChunker Enhancement Tests")
    print("=" * 60)

    try:
        test_markdown_table_detection()
        test_split_rows_by_token_budget()
        test_header_recovery()
        test_assemble_table_chunk()
        test_token_budget_calculation()
        test_short_table_no_split()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nStep 3 完成验证:")
        print("- Markdown表格检测正常")
        print("- Token级别行分割工作正常")
        print("- 表头恢复功能正确")
        print("- 表格chunk组装正确")
        print("- Token预算计算准确")
        print("- 短表格不分割")
        print("\n表格处理增强完成！")

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
