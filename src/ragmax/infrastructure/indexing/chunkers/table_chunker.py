from typing import Any

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.tokenization import Tokenizer
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class TableAwareChunker(BaseChunker):
    """表格感知分块器 - 增强版

    实现LightRAG的表格处理特性：
    - Markdown表格检测
    - 表头恢复（每个chunk重复表头）
    - Token级别的行分割
    """

    chunker_version = "v2-table-aware"

    def chunk(
        self, document: SourceDocument, config: dict[str, Any], tokenizer: Tokenizer
    ) -> list[IndexNode]:
        nodes: list[IndexNode] = []
        text_group: list[ContentBlock] = []
        section_path: tuple[str, ...] = ()

        def flush_text_group() -> None:
            if not text_group:
                return
            group_text = self._non_empty_text(text_group)
            for chunk in self._split_text(group_text, config, tokenizer):
                nodes.append(
                    self._make_node(
                        document=document,
                        chunker_name="table_aware", config=config,
                        text=chunk,
                        blocks=text_group,
                        section_path=section_path,
                        content_type="paragraph",
                        metadata=self._build_chunk_metadata(chunk, text_group, tokenizer),
                    )
                )
            text_group.clear()

        for block in document.blocks:
            if block.block_type == BlockType.HEADING:
                flush_text_group()
                section_path = self._push_heading(list(section_path), block.normalized_text)
                continue

            if block.block_type == BlockType.TABLE:
                flush_text_group()
                nodes.extend(self._table_nodes(document, config, block, section_path, tokenizer))
                continue

            if block.is_empty:
                continue

            text_group.append(block)

        flush_text_group()
        return nodes

    def _table_nodes(
        self,
        document: SourceDocument,
        config: dict[str, Any],
        table_block: ContentBlock,
        section_path: tuple[str, ...],
        tokenizer: Tokenizer,
    ) -> list[IndexNode]:
        """对表格块进行智能分块

        增强特性：
        - Token级别的行分割（不再是固定6行）
        - 表头恢复（每个chunk重复表头）
        - Markdown表格检测
        """
        repeat_header = config.get("repeat_table_header", True)

        chunks = self._split_table_with_header_recovery(
            table_text=table_block.normalized_text,
            chunk_size=int(config.get("chunk_size") or 600),
            tokenizer=tokenizer,
            repeat_header=repeat_header,
        )

        nodes: list[IndexNode] = []
        for chunk in chunks:
            nodes.append(
                self._make_node(
                    document=document,
                    chunker_name="table_aware", config=config,
                    text=chunk,
                    blocks=[table_block],
                    section_path=section_path,
                    content_type="table",
                    metadata={
                        **self._build_chunk_metadata(chunk, [table_block], tokenizer),
                        "table_header_recovered": repeat_header,
                    },
                )
            )
        return nodes

    def _split_table_with_header_recovery(
        self,
        table_text: str,
        chunk_size: int,
        tokenizer: Tokenizer,
        repeat_header: bool = True,
    ) -> list[str]:
        """使用表头恢复机制分割表格

        对齐LightRAG的表格处理逻辑：
        1. 检测Markdown表格
        2. 提取表头（前2行）
        3. 按Token budget分割表体
        4. 每个chunk重复表头

        Args:
            table_text: 表格文本
            chunk_size: 目标chunk大小（tokens）
            tokenizer: Token计数器
            repeat_header: 是否重复表头

        Returns:
            分块后的表格文本列表
        """
        lines = [line.strip() for line in table_text.splitlines() if line.strip()]

        # 短表格不需要分块
        if len(lines) <= 8:
            return [table_text.strip()]

        # 检测Markdown表格并提取表头
        header_lines = []
        body_lines = lines

        if repeat_header and self._is_markdown_table(lines):
            # Markdown表格：前2行是表头（标题行 + 分隔符）
            header_lines = lines[:2]
            body_lines = lines[2:]

        # 计算表头的token数
        header_text = "\n".join(header_lines) if header_lines else ""
        header_tokens = tokenizer.count_tokens(header_text) if header_lines else 0

        # 为表体分配token预算（预留表头空间 + 安全边距）
        safety_margin = 50  # 50 token安全边距
        body_budget = chunk_size - header_tokens - safety_margin

        # 确保body_budget合理
        if body_budget < 50:
            # 如果表头太大，使用更大的chunk或不重复表头
            return [table_text.strip()]

        # 按token预算分割表体行
        chunks = self._split_rows_by_token_budget(
            body_lines=body_lines,
            body_budget=body_budget,
            tokenizer=tokenizer,
        )

        # 重新组装表格（header + body）
        result = []
        for body_chunk in chunks:
            chunk = self._assemble_table_chunk(header_lines, body_chunk)
            result.append(chunk)

        return result

    def _is_markdown_table(self, lines: list[str]) -> bool:
        """检测是否为Markdown表格

        Markdown表格特征：
        - 第2行是分隔符（由 |-: 和空格组成）
        - 例如: |---|---|---| 或 | --- | --- |

        Args:
            lines: 表格行列表

        Returns:
            是否为Markdown表格
        """
        if len(lines) < 2:
            return False

        # 检查第二行是否为Markdown分隔符
        separator = lines[1].strip()

        # Markdown分隔符只包含 |, -, :, 和空格
        if not separator:
            return False

        # 移除空格后检查
        cleaned = separator.replace(" ", "")

        # 必须包含至少一个 - 和 |
        if "-" not in cleaned or "|" not in cleaned:
            return False

        # 只能包含允许的字符
        allowed_chars = set("|-: ")
        return all(c in allowed_chars for c in separator)

    def _split_rows_by_token_budget(
        self,
        body_lines: list[str],
        body_budget: int,
        tokenizer: Tokenizer,
    ) -> list[list[str]]:
        """按token预算分割行

        Args:
            body_lines: 表体行列表
            body_budget: 每个chunk的token预算
            tokenizer: Token计数器

        Returns:
            分组后的行列表
        """
        if not body_lines:
            return []

        chunks: list[list[str]] = []
        current_chunk: list[str] = []
        current_tokens = 0

        for line in body_lines:
            line_tokens = tokenizer.count_tokens(line)

            # 检查是否会超出预算
            if current_tokens + line_tokens > body_budget and current_chunk:
                # 保存当前chunk，开始新chunk
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0

            # 添加当前行
            current_chunk.append(line)
            current_tokens += line_tokens

        # 添加最后一个chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _assemble_table_chunk(
        self,
        header_lines: list[str],
        body_lines: list[str],
    ) -> str:
        """组装表格chunk（表头 + 表体）

        Args:
            header_lines: 表头行列表
            body_lines: 表体行列表

        Returns:
            组装后的表格文本
        """
        parts = header_lines + body_lines
        return "\n".join(parts)
