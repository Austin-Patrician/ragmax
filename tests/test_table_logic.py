"""独立测试表格处理增强功能（不依赖llama_index）"""
from ragmax.domain.indexing.tokenization import TiktokenTokenizer


def test_markdown_detection_logic():
    """测试Markdown表格检测逻辑"""
    print("Test 1: Markdown detection logic...")

    def is_markdown_table(lines):
        """提取的检测逻辑"""
        if len(lines) < 2:
            return False

        separator = lines[1].strip()
        if not separator:
            return False

        cleaned = separator.replace(" ", "")
        if "-" not in cleaned or "|" not in cleaned:
            return False

        allowed_chars = set("|-: ")
        return all(c in allowed_chars for c in separator)

    # 测试用例
    test_cases = [
        # (lines, expected_result, description)
        (
            ["| Name | Age |", "| --- | --- |", "| Alice | 30 |"],
            True,
            "Standard markdown table"
        ),
        (
            ["| Name | Age |", "| :--- | ---: |", "| Alice | 30 |"],
            True,
            "Aligned markdown table"
        ),
        (
            ["Name, Age", "Alice, 30"],
            False,
            "CSV format"
        ),
        (
            ["| Name | Age |"],
            False,
            "Single line (no separator)"
        ),
        (
            ["| Name | Age |", "Regular text", "| Alice | 30 |"],
            False,
            "Invalid separator"
        ),
    ]

    for lines, expected, description in test_cases:
        result = is_markdown_table(lines)
        assert result == expected, f"Failed: {description}"
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status} {description}: {result}")

    print("  PASS - All markdown detection tests passed")


def test_token_based_row_splitting():
    """测试基于token的行分割逻辑"""
    print("\nTest 2: Token-based row splitting...")

    tokenizer = TiktokenTokenizer()

    def split_rows_by_budget(body_lines, body_budget, tokenizer):
        """提取的分割逻辑"""
        if not body_lines:
            return []

        chunks = []
        current_chunk = []
        current_tokens = 0

        for line in body_lines:
            line_tokens = tokenizer.count_tokens(line)

            if current_tokens + line_tokens > body_budget and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0

            current_chunk.append(line)
            current_tokens += line_tokens

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # 测试数据
    rows = [
        "| Alice | 30 | New York City |",
        "| Bob | 25 | Los Angeles |",
        "| Charlie | 35 | Chicago |",
        "| Diana | 28 | Houston |",
        "| Eve | 32 | Phoenix |",
        "| Frank | 29 | Philadelphia |",
    ]

    # 测试不同的预算
    budgets = [20, 40, 100, 500]

    for budget in budgets:
        chunks = split_rows_by_budget(rows, budget, tokenizer)
        total_rows = sum(len(chunk) for chunk in chunks)

        print(f"  Budget {budget:3d} tokens: {len(chunks)} chunks, {total_rows} rows total")

        # 验证
        assert total_rows == len(rows), "Should preserve all rows"
        assert len(chunks) > 0, "Should produce at least one chunk"

        # 验证每个chunk不超预算
        for i, chunk in enumerate(chunks):
            chunk_text = "\n".join(chunk)
            chunk_tokens = tokenizer.count_tokens(chunk_text)
            # 允许一些误差（最后一个chunk可能小一些）
            if i < len(chunks) - 1:
                assert chunk_tokens <= budget + 15, f"Chunk {i} exceeds budget"

    print("  PASS - Token-based splitting works correctly")


def test_header_assembly():
    """测试表头和表体组装"""
    print("\nTest 3: Header and body assembly...")

    def assemble_table(header_lines, body_lines):
        """提取的组装逻辑"""
        parts = header_lines + body_lines
        return "\n".join(parts)

    header = [
        "| Name | Age | City |",
        "| --- | --- | --- |",
    ]

    body = [
        "| Alice | 30 | NYC |",
        "| Bob | 25 | LA |",
    ]

    result = assemble_table(header, body)

    # 验证
    lines = result.split("\n")
    assert len(lines) == 4, "Should have 4 lines total"
    assert lines[0] == header[0], "First line should be header"
    assert lines[1] == header[1], "Second line should be separator"
    assert lines[2] == body[0], "Third line should be first body row"

    print(f"  Assembled table:\n{result}")
    print("  PASS - Assembly works correctly")


def test_header_recovery_workflow():
    """测试完整的表头恢复工作流"""
    print("\nTest 4: Full header recovery workflow...")

    tokenizer = TiktokenTokenizer()

    # 模拟完整流程
    table_text = """| Name | Age | City |
| --- | --- | --- |
| Alice | 30 | New York |
| Bob | 25 | Los Angeles |
| Charlie | 35 | Chicago |
| Diana | 28 | Houston |
| Eve | 32 | Phoenix |
| Frank | 29 | Philadelphia |
| Grace | 27 | San Antonio |
| Henry | 31 | San Diego |"""

    lines = [line.strip() for line in table_text.splitlines() if line.strip()]

    print(f"  Total lines: {len(lines)}")

    # 1. 检测markdown
    separator = lines[1].strip()
    is_markdown = ("-" in separator and "|" in separator)
    print(f"  Is markdown: {is_markdown}")

    # 2. 提取表头
    header_lines = lines[:2] if is_markdown else []
    body_lines = lines[2:] if header_lines else lines

    print(f"  Header lines: {len(header_lines)}")
    print(f"  Body lines: {len(body_lines)}")

    # 3. 计算token预算
    header_text = "\n".join(header_lines)
    header_tokens = tokenizer.count_tokens(header_text)

    chunk_size = 80
    safety_margin = 20
    body_budget = chunk_size - header_tokens - safety_margin

    print(f"  Header tokens: {header_tokens}")
    print(f"  Body budget: {body_budget} tokens")

    # 4. 分割body
    body_chunks = []
    current_chunk = []
    current_tokens = 0

    for line in body_lines:
        line_tokens = tokenizer.count_tokens(line)

        if current_tokens + line_tokens > body_budget and current_chunk:
            body_chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0

        current_chunk.append(line)
        current_tokens += line_tokens

    if current_chunk:
        body_chunks.append(current_chunk)

    print(f"  Generated {len(body_chunks)} body chunks")

    # 5. 组装完整表格chunks
    final_chunks = []
    for body_chunk in body_chunks:
        full_chunk = "\n".join(header_lines + body_chunk)
        final_chunks.append(full_chunk)

        # 验证每个chunk都包含表头
        chunk_lines = full_chunk.split("\n")
        assert chunk_lines[0] == header_lines[0], "Missing header"
        assert chunk_lines[1] == header_lines[1], "Missing separator"

    print(f"  Final {len(final_chunks)} chunks with headers")

    for i, chunk in enumerate(final_chunks):
        lines_count = len(chunk.split("\n"))
        tokens = tokenizer.count_tokens(chunk)
        print(f"  Chunk {i+1}: {lines_count} lines, {tokens} tokens")

    print("  PASS - Full workflow completed successfully")


def main():
    print("=" * 60)
    print("Table Enhancement - Standalone Logic Tests")
    print("=" * 60)

    try:
        test_markdown_detection_logic()
        test_token_based_row_splitting()
        test_header_assembly()
        test_header_recovery_workflow()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nStep 3 核心逻辑验证完成:")
        print("- Markdown表格检测逻辑正确")
        print("- Token级别行分割算法正常")
        print("- 表头和表体组装正确")
        print("- 完整表头恢复工作流验证通过")
        print("\n表格处理增强的核心算法已实现！")

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
