"""语义向量分块器 - 对齐LightRAG的V策略

基于Embedding相似度的智能分块，在语义边界处切分文本。
"""

import re
from typing import Any

from ragmax.application.indexing.ports import EmbeddingProvider
from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.tokenization import Tokenizer
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class SemanticChunker(BaseChunker):
    """语义向量分块器

    使用Embedding相似度检测语义边界，实现智能分块。
    对齐LightRAG的V策略（Semantic Vector Chunking）。

    工作原理：
    1. 将文本分割成句子
    2. 为每个句子生成embedding向量
    3. 计算相邻句子的余弦相似度
    4. 在相似度突然下降的地方（语义断裂点）切分
    5. 合并相邻句子直到达到token限制

    特性：
    - 保持语义完整性
    - 自动检测话题转换
    - 适合研究论文、技术文档等有明确主题的内容
    """

    chunker_version = "v2-semantic-vector"

    def __init__(self, embedding_provider: EmbeddingProvider):
        """初始化语义分块器

        Args:
            embedding_provider: Embedding提供者，用于生成句子向量
        """
        self._embedding_provider = embedding_provider

    def chunk(
        self, document: SourceDocument, config: dict[str, Any], tokenizer: Tokenizer
    ) -> list[IndexNode]:
        """使用语义边界进行分块

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
        threshold_percentile = config.get("similarity_threshold_percentile", 75)
        chunker_name = "semantic_vector"

        for block in document.blocks:
            # 处理标题块
            if block.block_type == BlockType.HEADING:
                section_path = self._push_heading(list(section_path), block.normalized_text)
                continue

            # 跳过空块
            if block.is_empty:
                continue

            # 对文本块进行语义分块
            if block.block_type in {BlockType.TEXT, BlockType.OCR}:
                # 同步调用异步方法（在实际使用中由IndexingService处理）
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                chunk_texts = loop.run_until_complete(
                    self._semantic_split(
                        text=block.normalized_text,
                        chunk_size=chunk_size,
                        tokenizer=tokenizer,
                        threshold_percentile=threshold_percentile,
                    )
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
                            metadata={
                                **self._build_chunk_metadata(chunk_text, [block], tokenizer),
                                "chunking_method": "semantic_vector",
                            },
                        )
                    )

            # 表格保持完整
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

    async def _semantic_split(
        self,
        text: str,
        chunk_size: int,
        tokenizer: Tokenizer,
        threshold_percentile: int = 75,
    ) -> list[str]:
        """使用语义相似度进行文本分割

        核心算法：
        1. 分句
        2. 生成每个句子的embedding
        3. 计算相邻句子的余弦相似度
        4. 找到相似度低于阈值的位置作为breakpoint
        5. 在breakpoint处切分，并合并到token限制

        Args:
            text: 待分割的文本
            chunk_size: 目标chunk大小（tokens）
            tokenizer: Token计数器
            threshold_percentile: 相似度阈值百分位（0-100）

        Returns:
            分块后的文本列表
        """
        text = text.strip()
        if not text:
            return []

        # 1. 分句
        sentences = self._split_into_sentences(text)

        # 如果句子太少，不需要语义分割
        if len(sentences) <= 2:
            return [text]

        # 2. 生成embedding
        try:
            embeddings = await self._embedding_provider.embed(sentences)
        except Exception as e:
            # Embedding失败，回退到简单分割
            return self._fallback_split(text, chunk_size, tokenizer)

        # 3. 计算相邻句子的相似度
        similarities = self._calculate_similarities(embeddings)

        # 4. 找到语义断裂点（相似度低的位置）
        breakpoints = self._find_breakpoints(similarities, threshold_percentile)

        # 5. 根据breakpoints分组句子，并遵守token限制
        chunks = self._merge_by_breakpoints(
            sentences=sentences,
            breakpoints=breakpoints,
            chunk_size=chunk_size,
            tokenizer=tokenizer,
        )

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """将文本分割成句子

        支持中英文句子分隔符。

        Args:
            text: 待分割的文本

        Returns:
            句子列表
        """
        # 匹配句子结束符：. ! ? 。！？
        # 保留标点符号
        pattern = r'([.!?。！？]+[\s]*)'
        parts = re.split(pattern, text)

        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)

        # 处理最后一个部分（如果没有结束符）
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())

        return sentences if sentences else [text]

    def _calculate_similarities(self, embeddings: list[list[float]]) -> list[float]:
        """计算相邻embedding向量之间的余弦相似度

        Args:
            embeddings: Embedding向量列表

        Returns:
            相似度列表（长度为len(embeddings)-1）
        """
        similarities = []

        for i in range(len(embeddings) - 1):
            vec1 = embeddings[i]
            vec2 = embeddings[i + 1]

            # 计算余弦相似度
            similarity = self._cosine_similarity(vec1, vec2)
            similarities.append(similarity)

        return similarities

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的余弦相似度

        cosine_similarity = (A · B) / (||A|| * ||B||)

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            余弦相似度（-1到1之间，1表示完全相同）
        """
        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # 计算向量模长
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        # 避免除零
        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _find_breakpoints(
        self, similarities: list[float], threshold_percentile: int
    ) -> list[int]:
        """找到语义断裂点（相似度突然下降的位置）

        使用百分位数作为阈值，相似度低于阈值的位置是breakpoint。

        Args:
            similarities: 相似度列表
            threshold_percentile: 阈值百分位（0-100）

        Returns:
            Breakpoint索引列表
        """
        if not similarities:
            return []

        # 计算阈值（使用百分位数）
        sorted_sims = sorted(similarities)
        threshold_idx = int(len(sorted_sims) * threshold_percentile / 100)
        threshold = sorted_sims[threshold_idx] if threshold_idx < len(sorted_sims) else sorted_sims[-1]

        # 找到低于阈值的位置
        breakpoints = [i for i, sim in enumerate(similarities) if sim < threshold]

        return breakpoints

    def _merge_by_breakpoints(
        self,
        sentences: list[str],
        breakpoints: list[int],
        chunk_size: int,
        tokenizer: Tokenizer,
    ) -> list[str]:
        """根据breakpoints合并句子，遵守token限制

        策略：
        1. 在breakpoint处切分
        2. 如果切分后的段落超过chunk_size，进一步细分
        3. 如果段落太小，与下一段合并

        Args:
            sentences: 句子列表
            breakpoints: Breakpoint索引列表
            chunk_size: Token限制
            tokenizer: Token计数器

        Returns:
            合并后的文本块列表
        """
        # 添加开始和结束边界
        boundaries = [0] + [bp + 1 for bp in breakpoints] + [len(sentences)]

        chunks = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]

            # 合并这个段落的句子
            segment_sentences = sentences[start:end]
            segment_text = " ".join(segment_sentences)

            # 检查token数
            token_count = tokenizer.count_tokens(segment_text)

            if token_count <= chunk_size:
                # 在限制内，直接添加
                chunks.append(segment_text)
            else:
                # 超过限制，需要细分
                sub_chunks = self._split_by_token_limit(
                    segment_sentences, chunk_size, tokenizer
                )
                chunks.extend(sub_chunks)

        return chunks

    def _split_by_token_limit(
        self, sentences: list[str], chunk_size: int, tokenizer: Tokenizer
    ) -> list[str]:
        """将句子列表按token限制分割

        Args:
            sentences: 句子列表
            chunk_size: Token限制
            tokenizer: Token计数器

        Returns:
            分割后的文本块列表
        """
        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = tokenizer.count_tokens(sentence)

            # 如果加入这个句子会超限
            if current_tokens + sentence_tokens > chunk_size and current_chunk:
                # 保存当前chunk
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # 添加最后一个chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _fallback_split(
        self, text: str, chunk_size: int, tokenizer: Tokenizer
    ) -> list[str]:
        """Embedding失败时的回退策略

        使用简单的Token级别分割。

        Args:
            text: 待分割的文本
            chunk_size: Token限制
            tokenizer: Token计数器

        Returns:
            分割后的文本列表
        """
        tokens = tokenizer.encode(text)

        if len(tokens) <= chunk_size:
            return [text]

        chunks = []
        for i in range(0, len(tokens), chunk_size):
            chunk_tokens = tokens[i : i + chunk_size]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)

        return chunks
