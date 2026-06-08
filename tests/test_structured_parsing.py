"""
Tests for structured markdown parsing.
"""

import pytest

from ragmax.domain.indexing.blocks import BlockType
from ragmax.infrastructure.indexing.parsers.structured_parsing import markdown_to_blocks


def test_empty_markdown_returns_empty_list():
    blocks = markdown_to_blocks(source_id="test", markdown="")
    assert blocks == []

    blocks = markdown_to_blocks(source_id="test", markdown="   \n\n  ")
    assert blocks == []


def test_simple_paragraph():
    markdown = "This is a simple paragraph."
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    assert len(blocks) == 1
    assert blocks[0].block_type == BlockType.TEXT
    assert blocks[0].text == "This is a simple paragraph."
    assert blocks[0].block_id == "test:block:1"


def test_heading_levels():
    markdown = """
# Heading 1

## Heading 2

### Heading 3

#### Heading 4
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    headings = [b for b in blocks if b.block_type == BlockType.HEADING]
    assert len(headings) == 4
    assert headings[0].text == "Heading 1"
    assert headings[0].metadata["heading_level"] == 1
    assert headings[1].text == "Heading 2"
    assert headings[1].metadata["heading_level"] == 2
    assert headings[2].text == "Heading 3"
    assert headings[2].metadata["heading_level"] == 3
    assert headings[3].text == "Heading 4"
    assert headings[3].metadata["heading_level"] == 4


def test_section_hint_tracking():
    markdown = """
# Chapter 1

Some intro text.

## Section 1.1

Section content.

### Subsection 1.1.1

Detailed content.
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    # Find blocks by type
    h1 = next(b for b in blocks if b.text == "Chapter 1")
    h2 = next(b for b in blocks if b.text == "Section 1.1")
    h3 = next(b for b in blocks if b.text == "Subsection 1.1.1")

    # Check section_hint hierarchy
    assert h1.section_hint == ("Chapter 1",)
    assert h2.section_hint == ("Chapter 1", "Section 1.1")
    assert h3.section_hint == ("Chapter 1", "Section 1.1", "Subsection 1.1.1")


def test_code_block_with_language():
    markdown = '''
# Code Example

```python
def hello():
    print("world")
```
'''
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    code_blocks = [b for b in blocks if b.block_type == BlockType.CODE]
    assert len(code_blocks) == 1
    assert "```python" in code_blocks[0].text
    assert 'def hello():' in code_blocks[0].text
    assert code_blocks[0].metadata["language"] == "python"


def test_code_block_without_language():
    markdown = '''
```
plain code block
```
'''
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    code_blocks = [b for b in blocks if b.block_type == BlockType.CODE]
    assert len(code_blocks) == 1
    assert "plain code block" in code_blocks[0].text
    assert code_blocks[0].metadata["language"] == ""


def test_table_parsing():
    markdown = """
| Name  | Age | City |
|-------|-----|------|
| Alice | 25  | NYC  |
| Bob   | 30  | LA   |
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    tables = [b for b in blocks if b.block_type == BlockType.TABLE]
    assert len(tables) == 1
    table_text = tables[0].text
    assert "Name" in table_text
    assert "Alice" in table_text
    assert "Bob" in table_text
    assert "|" in table_text  # Markdown table format preserved


def test_unordered_list():
    markdown = """
Shopping list:

- Apples
- Bananas
- Oranges
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    lists = [b for b in blocks if b.block_type == BlockType.LIST]
    assert len(lists) == 1
    assert lists[0].metadata["list_type"] == "unordered"
    assert "Apples" in lists[0].text
    assert "Bananas" in lists[0].text
    assert "Oranges" in lists[0].text


def test_ordered_list():
    markdown = """
Steps:

1. First step
2. Second step
3. Third step
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    lists = [b for b in blocks if b.block_type == BlockType.LIST]
    assert len(lists) == 1
    assert lists[0].metadata["list_type"] == "ordered"
    assert "First step" in lists[0].text
    assert "Second step" in lists[0].text


def test_blockquote():
    markdown = """
> This is a quote.
> It spans multiple lines.
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    quotes = [b for b in blocks if b.block_type == BlockType.QUOTE]
    assert len(quotes) == 1
    assert "> This is a quote." in quotes[0].text
    assert "> It spans multiple lines." in quotes[0].text


def test_complex_document_all_block_types():
    markdown = """
# Main Title

Introduction paragraph with some text.

## Features

Key features:

- Feature 1
- Feature 2
- Feature 3

## Code Example

Here's some code:

```python
def process(data):
    return data * 2
```

## Data Table

| Metric | Value |
|--------|-------|
| CPU    | 80%   |
| Memory | 60%   |

> Note: All metrics are averages.

### Conclusion

Final thoughts here.
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    # Verify all block types are present
    block_types = {b.block_type for b in blocks}
    assert BlockType.HEADING in block_types
    assert BlockType.TEXT in block_types
    assert BlockType.LIST in block_types
    assert BlockType.CODE in block_types
    assert BlockType.TABLE in block_types
    assert BlockType.QUOTE in block_types

    # Verify count
    assert len([b for b in blocks if b.block_type == BlockType.HEADING]) == 5  # Includes h3
    assert len([b for b in blocks if b.block_type == BlockType.CODE]) == 1
    assert len([b for b in blocks if b.block_type == BlockType.TABLE]) == 1
    assert len([b for b in blocks if b.block_type == BlockType.LIST]) == 1
    assert len([b for b in blocks if b.block_type == BlockType.QUOTE]) == 1


def test_page_number_propagation():
    markdown = "# Test\n\nContent here."
    blocks = markdown_to_blocks(source_id="test", markdown=markdown, page_no=5)

    assert all(b.page_no == 5 for b in blocks)


def test_metadata_propagation():
    markdown = "# Test\n\nContent."
    custom_metadata = {"source": "llamaparse", "tier": "agentic"}
    blocks = markdown_to_blocks(source_id="test", markdown=markdown, metadata=custom_metadata)

    for block in blocks:
        assert block.metadata["source"] == "llamaparse"
        assert block.metadata["tier"] == "agentic"


def test_block_id_sequential():
    markdown = """
# Title

Paragraph 1.

Paragraph 2.

Paragraph 3.
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown, start_index=10)

    assert blocks[0].block_id == "test:block:10"
    assert blocks[1].block_id == "test:block:11"
    assert blocks[2].block_id == "test:block:12"
    assert blocks[3].block_id == "test:block:13"


def test_nested_lists():
    markdown = """
- Level 1 item
  - Level 2 item
  - Another level 2
- Back to level 1
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    lists = [b for b in blocks if b.block_type == BlockType.LIST]
    assert len(lists) == 1
    # Verify nesting is preserved in text (at least level 2 items should be indented)
    assert "Level 2 item" in lists[0].text
    assert "Back to level 1" in lists[0].text
    assert "Level 2 item" in lists[0].text


def test_inline_code_in_paragraph():
    markdown = "Use the `print()` function to output text."
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    # Inline code should be part of TEXT block, not CODE block
    assert len(blocks) == 1
    assert blocks[0].block_type == BlockType.TEXT
    assert "print()" in blocks[0].text


def test_multiple_paragraphs():
    markdown = """
First paragraph.

Second paragraph.

Third paragraph.
"""
    blocks = markdown_to_blocks(source_id="test", markdown=markdown)

    text_blocks = [b for b in blocks if b.block_type == BlockType.TEXT]
    assert len(text_blocks) == 3
    assert text_blocks[0].text == "First paragraph."
    assert text_blocks[1].text == "Second paragraph."
    assert text_blocks[2].text == "Third paragraph."
