"""固定Token大小分块策略 - 对齐LightRAG的F策略

实现基于Token级别的滑动窗口分块，提供精确的chunk大小控制。
"""
from typing import Any

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.tokenization import Tokenizer
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class FixedTokenChunker(BaseChunker):
    """固定Token大小分块器

    使用Token级别的滑动窗口进行文本分块，对齐LightRAG的F策略。
    相比字符级别分块，Token级别分块提供更精确的chunk大小控制。

    特性：
    - Token级别的滑动窗口
    - 可配置的chunk size和overlap
    - 保持section path和heading层级
    - 支持多种block类型（TEXT, OCR, TABLE等）
    """

    chunker_version = "v2-fixed-token"

    def chunk(
        self, document: SourceDocument, config: dict[str, Any], tokenizer: Tokenizer
    ) -> list[IndexNode]:
        """对文档进行固定Token大小分块

        Args:
            document: 源文档
            config: 分块配置
            tokenizer: Token计数器

        Returns:
            分块后的IndexNode列表
        """
        nodes: list[IndexNode] = []
        section_path: tuple[str, ...] = ()

        chunk_size = config.get("chunk_size", 1000)
        chunk_overlap = config.get("chunk_overlap", 100)
        chunker_name = "fixed_token"

        for block in document.blocks:
            # 处理标题块，更新section path
            if block.block_type == BlockType.HEADING:
                section_path = self._push_heading(list(section_path), block.normalized_text)
                continue

            # 跳过空块
            if block.is_empty:
                continue

            # 对文本块和OCR块进行分块
            if block.block_type in {BlockType.TEXT, BlockType.OCR}:
                chunk_texts = self._split_by_tokens(
                    text=block.normalized_text,
                    chunk_size=chunk_size,
                    overlap=chunk_overlap,
                    tokenizer=tokenizer,
                )

                for chunk_text in chunk_texts:
                    nodes.append(
                        self._make_node(
                            document=document,
                            chunker_name=chunker_name,
                            config=config,
                            text=chunk_text,
                            blocks=[block],
                            section_path=section_path,
                            content_type="paragraph",
                            metadata=self._build_chunk_metadata(chunk_text, [block], tokenizer),
                        )
                    )

            # 表格块保持完整，不分块
            elif block.block_type == BlockType.TABLE:
                nodes.append(
                    self._make_node(
                        document=document,
                        chunker_name=chunker_name,
                        config=config,
                        text=block.normalized_text,
                        blocks=[block],
                        section_path=section_path,
                        content_type="table",
                        metadata=self._build_chunk_metadata(
                            block.normalized_text, [block], tokenizer
                        ),
                    )
                )

        return nodes

    def _split_by_tokens(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        tokenizer: Tokenizer,
    ) -> list[str]:
        """使用Token级别滑动窗口分割文本

        这是核心算法，对齐LightRAG的chunking_by_token_size实现。

        算法：
        1. 将文本编码为token列表
        2. 使用滑动窗口遍历token列表
        3. 每个窗口大小为chunk_size，步长为(chunk_size - overlap)
        4. 将每个窗口的tokens解码回文本

        Args:
            text: 待分割的文本
            chunk_size: 每个chunk的目标token数
            overlap: 相邻chunk之间的重叠token数
            tokenizer: Token编码器

        Returns:
            分块后的文本列表
        """
        text = text.strip()
        if not text:
            return []

        # 1. 编码为tokens
        tokens = tokenizer.encode(text)
        total_tokens = len(tokens)

        # 如果文本很短，不需要分块
        if total_tokens <= chunk_size:
            return [text]

        # 2. 滑动窗口分块
        chunks: list[str] = []
        step = chunk_size - overlap  # 滑动步长

        # 确保step至少为1，避免无限循环
        if step <= 0:
            step = max(1, chunk_size // 2)

        start = 0
        while start < total_tokens:
            # 窗口结束位置
            end = min(start + chunk_size, total_tokens)

            # 提取窗口内的tokens
            window_tokens = tokens[start:end]

            # 解码为文本
            chunk_text = tokenizer.decode(window_tokens).strip()

            if chunk_text:  # 只添加非空chunk
                chunks.append(chunk_text)

            # 如果已经到达末尾，退出
            if end >= total_tokens:
                break

            # 移动窗口
            start += step

        return chunks
