"""
Structured parsing for markdown and other formatted text.

This module provides precise parsing of structured content (markdown, HTML, etc.)
to preserve document structure instead of flattening it with simple regex splitting.
"""

from collections.abc import Mapping
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from ragmax.domain.indexing.blocks import BlockType, ContentBlock


def markdown_to_blocks(
    *,
    source_id: str,
    markdown: str,
    start_index: int = 1,
    page_no: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> list[ContentBlock]:
    """
    Parse markdown text into structured ContentBlocks using markdown-it-py.

    Preserves document structure by identifying:
    - Headings (h1-h6) with correct levels
    - Code blocks with language tags
    - Tables with structure
    - Lists (ordered/unordered/nested)
    - Blockquotes
    - Paragraphs

    Args:
        source_id: Unique identifier for the source document
        markdown: Markdown text to parse
        start_index: Starting block index (for numbering)
        page_no: Optional page number
        metadata: Optional metadata dict to attach to all blocks

    Returns:
        List of ContentBlock objects with accurate block_type classification
    """
    if not markdown or not markdown.strip():
        return []

    # Use commonmark with table plugin enabled
    md = MarkdownIt("commonmark").enable("table")
    tokens = md.parse(markdown)

    blocks: list[ContentBlock] = []
    current_section_path: list[str] = []
    block_index = start_index

    # Process tokens to build blocks
    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            # Heading: heading_open -> inline -> heading_close
            heading_level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
            inline_token = tokens[i + 1] if i + 1 < len(tokens) else None

            if inline_token and inline_token.type == "inline":
                heading_text = inline_token.content

                # Update section path
                current_section_path = _update_section_path(
                    current_section_path, heading_text, heading_level
                )

                blocks.append(
                    ContentBlock(
                        block_id=f"{source_id}:block:{block_index}",
                        source_id=source_id,
                        block_type=BlockType.HEADING,
                        text=heading_text,
                        page_no=page_no,
                        section_hint=tuple(current_section_path),
                        metadata={
                            **(metadata or {}),
                            "heading_level": heading_level,
                        },
                    )
                )
                block_index += 1

            i += 3  # Skip heading_open, inline, heading_close

        elif token.type == "fence":
            # Code block
            code_text = token.content
            language = token.info.strip() if token.info else ""

            # Preserve code fence markers for context
            if language:
                formatted_text = f"```{language}\n{code_text}```"
            else:
                formatted_text = f"```\n{code_text}```"

            blocks.append(
                ContentBlock(
                    block_id=f"{source_id}:block:{block_index}",
                    source_id=source_id,
                    block_type=BlockType.CODE,
                    text=formatted_text,
                    page_no=page_no,
                    section_hint=tuple(current_section_path),
                    metadata={
                        **(metadata or {}),
                        "language": language,
                        "code_length": len(code_text),
                    },
                )
            )
            block_index += 1
            i += 1

        elif token.type == "table_open":
            # Table: extract until table_close
            table_tokens, table_end_idx = _extract_table_tokens(tokens, i)
            table_text = _render_table_as_markdown(table_tokens)

            if table_text.strip():
                blocks.append(
                    ContentBlock(
                        block_id=f"{source_id}:block:{block_index}",
                        source_id=source_id,
                        block_type=BlockType.TABLE,
                        text=table_text,
                        page_no=page_no,
                        section_hint=tuple(current_section_path),
                        metadata={**(metadata or {})},
                    )
                )
                block_index += 1

            i = table_end_idx + 1

        elif token.type == "bullet_list_open" or token.type == "ordered_list_open":
            # List: extract until list_close
            list_tokens, list_end_idx = _extract_list_tokens(tokens, i)
            list_text = _render_list_as_text(list_tokens, ordered=(token.type == "ordered_list_open"))

            if list_text.strip():
                blocks.append(
                    ContentBlock(
                        block_id=f"{source_id}:block:{block_index}",
                        source_id=source_id,
                        block_type=BlockType.LIST,
                        text=list_text,
                        page_no=page_no,
                        section_hint=tuple(current_section_path),
                        metadata={
                            **(metadata or {}),
                            "list_type": "ordered" if token.type == "ordered_list_open" else "unordered",
                        },
                    )
                )
                block_index += 1

            i = list_end_idx + 1

        elif token.type == "blockquote_open":
            # Blockquote: extract until blockquote_close
            quote_tokens, quote_end_idx = _extract_blockquote_tokens(tokens, i)
            quote_text = _render_blockquote_as_text(quote_tokens)

            if quote_text.strip():
                blocks.append(
                    ContentBlock(
                        block_id=f"{source_id}:block:{block_index}",
                        source_id=source_id,
                        block_type=BlockType.QUOTE,
                        text=quote_text,
                        page_no=page_no,
                        section_hint=tuple(current_section_path),
                        metadata={**(metadata or {})},
                    )
                )
                block_index += 1

            i = quote_end_idx + 1

        elif token.type == "paragraph_open":
            # Paragraph: paragraph_open -> inline -> paragraph_close
            inline_token = tokens[i + 1] if i + 1 < len(tokens) else None

            if inline_token and inline_token.type == "inline" and inline_token.content.strip():
                blocks.append(
                    ContentBlock(
                        block_id=f"{source_id}:block:{block_index}",
                        source_id=source_id,
                        block_type=BlockType.TEXT,
                        text=inline_token.content,
                        page_no=page_no,
                        section_hint=tuple(current_section_path),
                        metadata={**(metadata or {})},
                    )
                )
                block_index += 1

            i += 3  # Skip paragraph_open, inline, paragraph_close

        else:
            i += 1

    return blocks


def _update_section_path(
    current_path: list[str],
    heading_text: str,
    level: int,
) -> list[str]:
    """
    Update section path based on heading level.

    Examples:
        Level 1: ["Introduction"]
        Level 2: ["Introduction", "Background"]
        Level 3: ["Introduction", "Background", "History"]
    """
    # Truncate path to level - 1, then append new heading
    new_path = current_path[: max(0, level - 1)]
    new_path.append(heading_text)
    return new_path


def _extract_table_tokens(tokens: list[Token], start_idx: int) -> tuple[list[Token], int]:
    """Extract all tokens from table_open to table_close."""
    table_tokens = []
    depth = 0
    i = start_idx

    while i < len(tokens):
        token = tokens[i]
        table_tokens.append(token)

        if token.type == "table_open":
            depth += 1
        elif token.type == "table_close":
            depth -= 1
            if depth == 0:
                return table_tokens, i

        i += 1

    return table_tokens, len(tokens) - 1


def _render_table_as_markdown(table_tokens: list[Token]) -> str:
    """Render table tokens back as markdown table."""
    rows: list[list[str]] = []
    current_row: list[str] = []
    is_header = True

    for token in table_tokens:
        if token.type == "tr_open":
            current_row = []
        elif token.type == "tr_close":
            if current_row:
                rows.append(current_row)
            current_row = []
        elif token.type in ("th_open", "td_open"):
            pass
        elif token.type in ("th_close", "td_close"):
            pass
        elif token.type == "inline" and token.content:
            current_row.append(token.content)
        elif token.type == "thead_close":
            is_header = False

    if not rows:
        return ""

    # Build markdown table
    lines = []

    # Header row
    if rows:
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("|" + "|".join(["---"] * len(rows[0])) + "|")

    # Data rows
    for row in rows[1:]:
        # Pad row to match header length
        padded_row = row + [""] * (len(rows[0]) - len(row))
        lines.append("| " + " | ".join(padded_row) + " |")

    return "\n".join(lines)


def _extract_list_tokens(tokens: list[Token], start_idx: int) -> tuple[list[Token], int]:
    """Extract all tokens from list_open to list_close."""
    list_tokens = []
    depth = 0
    i = start_idx

    while i < len(tokens):
        token = tokens[i]
        list_tokens.append(token)

        if token.type in ("bullet_list_open", "ordered_list_open"):
            depth += 1
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            depth -= 1
            if depth == 0:
                return list_tokens, i

        i += 1

    return list_tokens, len(tokens) - 1


def _render_list_as_text(list_tokens: list[Token], ordered: bool) -> str:
    """Render list tokens as plain text with markers."""
    lines = []
    item_number = [1]  # Stack for tracking numbers at each level
    indent_level = 0
    in_item = False
    item_content = []
    current_list_ordered = ordered

    for token in list_tokens:
        if token.type == "list_item_open":
            in_item = True
            item_content = []
        elif token.type == "list_item_close":
            if item_content:
                indent = "  " * max(0, indent_level - 1)
                if current_list_ordered and item_number:
                    marker = f"{item_number[-1]}."
                    item_number[-1] += 1
                else:
                    marker = "-"
                lines.append(f"{indent}{marker} {' '.join(item_content)}")
            in_item = False
        elif token.type in ("bullet_list_open", "ordered_list_open"):
            if indent_level > 0:  # Nested list
                if token.type == "ordered_list_open":
                    item_number.append(1)
            indent_level += 1
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            indent_level = max(0, indent_level - 1)
            if token.type == "ordered_list_close" and len(item_number) > 1:
                item_number.pop()
        elif token.type == "inline" and in_item:
            if token.content:
                item_content.append(token.content)

    return "\n".join(lines)


def _extract_blockquote_tokens(tokens: list[Token], start_idx: int) -> tuple[list[Token], int]:
    """Extract all tokens from blockquote_open to blockquote_close."""
    quote_tokens = []
    depth = 0
    i = start_idx

    while i < len(tokens):
        token = tokens[i]
        quote_tokens.append(token)

        if token.type == "blockquote_open":
            depth += 1
        elif token.type == "blockquote_close":
            depth -= 1
            if depth == 0:
                return quote_tokens, i

        i += 1

    return quote_tokens, len(tokens) - 1


def _render_blockquote_as_text(quote_tokens: list[Token]) -> str:
    """Render blockquote tokens as text with > prefix."""
    lines = []

    for token in quote_tokens:
        if token.type == "inline" and token.content:
            # Prefix each line with >
            for line in token.content.split("\n"):
                lines.append(f"> {line}")

    return "\n".join(lines)
