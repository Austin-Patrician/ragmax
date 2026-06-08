# Retrieval Pipeline 完整实现计划

## 用户决策

- **BM25 实现**: Qdrant Sparse Vectors（原生支持，与现有向量搜索统一）
- **精排方式**: BGE-Reranker-v2-m3（本地推理，开源模型）
- **答案生成**: LLM-based（OpenAI/自定义 LLM，支持自然语言生成）
- **实现顺序**: 完整实现（Phase 1-5 按顺序）

## 实现策略

### 设计原则
1. **保持现有架构一致性**: 遵循项目的 Ports & Adapters 架构模式
2. **可配置化**: 所有新组件都可通过配置文件启用/禁用
3. **向后兼容**: 不破坏现有的 retrieval API 和功能
4. **渐进式增强**: 每个 Phase 独立可测试，可单独启用

### 现有实现分析

**已实现功能**:
- ✅ 向量搜索 (`QdrantVectorSearcher`)
- ✅ 父子节点关系 (`parent_node_id`)
- ✅ 关键词粗排 (`ScoreKeywordReranker`)
- ✅ 提取式答案生成 (`ExtractiveAnswerGenerator`)
- ✅ 嵌入提供者 (Hash/OpenAI)
- ✅ 引用追踪
- ✅ 上下文扩展（child → parent）

**需要新增**:
- ❌ Query Transformation（查询转换）
- ❌ BM25 词法搜索（Qdrant Sparse Vectors）
- ❌ RRF 融合算法
- ❌ Cross-encoder 精排（BGE Reranker）
- ❌ LLM 答案生成器
- ❌ 多查询变体支持
- ❌ 高级上下文构建策略

---

## Phase 1: Query Processing Layer（查询处理层）

### 1.1 增强 Query Normalization

**目标**: 增强现有的 `_normalize_query` 函数

**文件**: 新建 `src/ragmax/infrastructure/retrieval/query/normalizer.py`

**实现内容**:
```python
class QueryNormalizer(Protocol):
    def normalize(self, query: str) -> NormalizedQuery

@dataclass(frozen=True)
class NormalizedQuery:
    original: str
    normalized: str
    language: str | None
```

**实现类**:
- `BasicQueryNormalizer`: 去除多余空格、特殊字符
- 暂不实现语言检测和拼写纠正（可后续扩展）

### 1.2 Query Transformer

**目标**: 支持多种查询转换策略

**文件**: 新建 `src/ragmax/infrastructure/retrieval/query/transformer.py`

**实现内容**:
```python
class QueryTransformer(Protocol):
    async def transform(self, query: NormalizedQuery, strategy: str) -> TransformedQuery

@dataclass(frozen=True)
class TransformedQuery:
    original: str
    variants: list[str]  # 查询变体（HyDE、Multi-Query 等）
    strategy: str
    metadata: dict[str, Any]
```

**实现类**:
- `OriginalQueryTransformer`: 不转换（默认）
- `HyDETransformer`: 生成假设性文档
- `MultiQueryTransformer`: 生成 3-5 个查询变体
- 使用 LLM Client 接口（支持 OpenAI）

### 1.3 配置项

```python
# config.py 新增
retrieval_query_transformation: str = "original"  # "original" | "hyde" | "multi_query"
retrieval_query_multi_query_count: int = 3
```

---

## Phase 2: Hybrid Retrieval Layer（混合检索层）

### 2.1 BM25 Searcher（Qdrant Sparse Vectors）

**目标**: 实现基于 Qdrant 稀疏向量的 BM25 搜索

**文件**: 新建 `src/ragmax/infrastructure/qdrant/sparse_searcher.py`

**实现内容**:
```python
@dataclass(frozen=True)
class BM25SearchHit:
    node_id: str
    score: float
    matched_terms: list[str]

class BM25Searcher(Protocol):
    async def search(...) -> tuple[BM25SearchHit, ...]

class QdrantSparseBM25Searcher:
    """使用 Qdrant 原生稀疏向量实现 BM25"""
    
    def _text_to_sparse_vector(self, text: str) -> dict[int, float]:
        """将文本转换为 BM25 风格的稀疏向量"""
        # 使用简单的 tokenization + TF-IDF 权重
    
    async def search(self, query: str, ...) -> tuple[BM25SearchHit, ...]
```

**数据准备**:
- **不需要数据库迁移**（Qdrant 存储稀疏向量）
- 需要在 indexing 阶段为每个节点生成稀疏向量
- 修改 `QdrantVectorIndexWriter` 支持同时写入 dense + sparse vectors

### 2.2 RRF Fusion

**目标**: 融合向量搜索和 BM25 搜索结果

**文件**: 新建 `src/ragmax/infrastructure/retrieval/fusion/rrf_fuser.py`

**实现内容**:
```python
@dataclass(frozen=True)
class FusedSearchHit:
    node_id: str
    fused_score: float
    vector_score: float | None
    bm25_score: float | None
    vector_rank: int | None
    bm25_rank: int | None

class SearchFuser(Protocol):
    def fuse(
        self,
        vector_hits: tuple[VectorSearchHit, ...],
        bm25_hits: tuple[BM25SearchHit, ...],
        top_k: int
    ) -> tuple[FusedSearchHit, ...]

class RRFFuser:
    """Reciprocal Rank Fusion: score = Σ 1/(k + rank)"""
    
    def __init__(self, k: int = 60):
        self.k = k
```

### 2.3 增强 VectorSearcher

**目标**: 支持多查询向量搜索

**文件**: 修改 `src/ragmax/infrastructure/qdrant/vector_searcher.py`

**实现内容**:
```python
class QdrantVectorSearcher:
    async def search_multi_query(
        self,
        query_vectors: Sequence[Sequence[float]],
        ...
    ) -> tuple[VectorSearchHit, ...]:
        """支持多个查询向量，合并去重结果"""
```

### 2.4 修改 RetrievalService

**目标**: 整合混合搜索流程

**文件**: 修改 `src/ragmax/application/retrieval/service.py`

**变更**:
```python
class RetrievalService:
    def __init__(
        self,
        ...,
        bm25_searcher: BM25Searcher | None = None,
        search_fuser: SearchFuser | None = None,
        query_transformer: QueryTransformer | None = None,
    ):
        ...
    
    async def search(self, command: RetrievalCommand) -> RetrievalResult:
        # 1. Query normalization & transformation
        normalized = self._query_normalizer.normalize(command.query)
        transformed = await self._query_transformer.transform(normalized)
        
        # 2. Parallel search: Vector + BM25
        vector_hits = await self._vector_search_all_variants(transformed)
        bm25_hits = await self._bm25_search_all_variants(transformed) if bm25 enabled
        
        # 3. Fusion
        fused_hits = self._fuser.fuse(vector_hits, bm25_hits, top_k)
        
        # 4. Hydrate nodes (same as before)
        ...
```

### 2.5 配置项

```python
# config.py 新增
retrieval_bm25_enabled: bool = False
retrieval_bm25_top_k: int = 100
retrieval_fusion_strategy: str = "rrf"  # "rrf" | "weighted" | "none"
retrieval_fusion_rrf_k: int = 60
```

---

## Phase 3: Reranking Layer（重排层）

### 3.1 BGE Cross-Encoder Reranker

**目标**: 实现基于 BGE Reranker 的精排

**文件**: 新建 `src/ragmax/infrastructure/retrieval/rerankers/bge_reranker.py`

**依赖**: 需要安装 `sentence-transformers`

**实现内容**:
```python
from sentence_transformers import CrossEncoder

class BGECrossEncoderReranker:
    name = "bge_reranker:v2-m3"
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = "cpu"):
        self.model = CrossEncoder(model_name, device=device)
    
    async def rerank(
        self,
        query: str,
        nodes: Sequence[RetrievedNode],
        top_k: int,
    ) -> tuple[RerankedNode, ...]:
        # Prepare pairs: [(query, node.text) for node in nodes]
        # Batch inference: scores = self.model.predict(pairs, batch_size=32)
        # Sort by score, return top_k
```

### 3.2 Two-Stage Reranking

**目标**: 粗排 → 精排两阶段策略

**文件**: 修改 `src/ragmax/application/retrieval/service.py`

**实现内容**:
```python
class RetrievalService:
    async def answer(self, command: AnswerCommand) -> AnswerResult:
        # 1. Retrieval (vector + bm25 + fusion)
        retrieval_result = await self.search(...)
        
        # 2. Coarse reranking (keyword, top 100)
        coarse_reranked = await self._coarse_reranker.rerank(
            query, retrieval_result.results, top_k=100
        )
        
        # 3. Fine reranking (cross-encoder, top 20)
        fine_reranked = await self._fine_reranker.rerank(
            query, coarse_reranked, top_k=20
        ) if self._fine_reranker else coarse_reranked
        
        # 4. Build context & generate answer
        ...
```

### 3.3 配置项

```python
# config.py 新增
retrieval_reranking_stages: list[str] = ["coarse"]  # ["coarse", "fine"]
retrieval_reranker_fine: str = "bge"  # "bge" | "none"
retrieval_reranker_fine_model: str = "BAAI/bge-reranker-v2-m3"
retrieval_reranker_fine_device: str = "cpu"  # "cpu" | "cuda"
retrieval_reranker_coarse_top_k: int = 100
retrieval_reranker_fine_top_k: int = 20
```

---

## Phase 4: Context Building Layer（上下文构建层）

### 4.1 增强 Parent-Child Context Injection

**目标**: 支持多种上下文策略

**文件**: 新建 `src/ragmax/infrastructure/retrieval/context/context_builder.py`

**实现内容**:
```python
class ContextStrategy(str, Enum):
    CHILD_ONLY = "child_only"
    PARENT_ONLY = "parent_only"
    CHILD_WITH_PARENT = "child_with_parent"
    SENTENCE_WINDOW = "sentence_window"

@dataclass(frozen=True)
class EnhancedContextItem:
    node_id: str
    text: str
    strategy: ContextStrategy
    parent_node_id: str | None
    parent_text: str | None
    metadata: dict[str, Any]

class ContextBuilder:
    def __init__(self, strategy: ContextStrategy = ContextStrategy.CHILD_WITH_PARENT):
        self.strategy = strategy
    
    async def build_contexts(
        self,
        reranked_nodes: Sequence[RerankedNode],
        node_repository: IndexNodeRepository,
    ) -> tuple[EnhancedContextItem, ...]:
        # 根据 strategy 构建不同的上下文
```

### 4.2 Context Deduplication

**目标**: 去除重复或高度重叠的上下文

**实现内容**:
```python
class ContextDeduplicator:
    def __init__(self, similarity_threshold: float = 0.95):
        self.threshold = similarity_threshold
    
    def deduplicate(
        self,
        contexts: Sequence[EnhancedContextItem],
    ) -> tuple[EnhancedContextItem, ...]:
        # 使用 Jaccard similarity 或简单的字符串匹配
        # 保留得分最高的版本
```

### 4.3 修改 RetrievalService

**目标**: 使用新的 ContextBuilder

**文件**: 修改 `src/ragmax/application/retrieval/service.py`

**变更**:
```python
# 替换 _context_items_from_reranked 函数
contexts = await self._context_builder.build_contexts(fine_reranked, ...)
contexts = self._deduplicator.deduplicate(contexts)
```

### 4.4 配置项

```python
# config.py 新增
retrieval_context_strategy: str = "child_with_parent"
retrieval_context_max_length: int = 2000
retrieval_context_deduplication_threshold: float = 0.95
```

---

## Phase 5: Answer Generation Layer（答案生成层）

### 5.1 LLM Client 接口

**目标**: 统一的 LLM 调用接口

**文件**: 新建 `src/ragmax/infrastructure/llm/client.py`

**实现内容**:
```python
@dataclass(frozen=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str

@dataclass(frozen=True)
class LLMResponse:
    content: str
    usage: dict[str, int]  # tokens used
    model: str

class LLMClient(Protocol):
    async def generate(
        self,
        messages: Sequence[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        ...

class OpenAILLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    async def generate(self, messages, ...) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(...)
```

### 5.2 LLM Answer Generator

**目标**: 基于 LLM 生成自然语言答案

**文件**: 新建 `src/ragmax/infrastructure/retrieval/answer_generators/llm_answer_generator.py`

**实现内容**:
```python
class LLMAnswerGenerator:
    name = "llm_answer_generator:v1"
    
    def __init__(
        self,
        llm_client: LLMClient,
        max_context_items: int = 8,
        temperature: float = 0.0,
    ):
        self.llm = llm_client
        self.max_context_items = max_context_items
        self.temperature = temperature
    
    async def generate(
        self,
        query: str,
        contexts: Sequence[RetrievalContextItem],
    ) -> GeneratedAnswer:
        # 1. Build prompt with contexts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query, contexts)
        
        # 2. Call LLM
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        response = await self.llm.generate(messages, temperature=self.temperature)
        
        # 3. Extract citations from response
        answer, used_context_ids = self._parse_answer_with_citations(response.content)
        
        return GeneratedAnswer(
            answer=answer,
            used_context_ids=tuple(used_context_ids),
            metadata={
                "strategy": "llm_generation",
                "model": response.model,
                "usage": response.usage,
            },
        )
    
    def _build_system_prompt(self) -> str:
        return """You are a helpful assistant that answers questions based on the provided context.

Rules:
1. ONLY use information from the provided context passages
2. Cite your sources using [1], [2], etc. matching the passage numbers
3. If the context doesn't contain enough information, say so clearly
4. Be concise but complete
5. Do not use external knowledge"""
    
    def _build_user_prompt(self, query: str, contexts: Sequence[RetrievalContextItem]) -> str:
        context_text = "\n\n".join([
            f"[{ctx.citation_id}] {ctx.text}"
            for ctx in contexts[:self.max_context_items]
        ])
        
        return f"""Context passages:

{context_text}

Question: {query}

Answer:"""
    
    def _parse_answer_with_citations(self, answer: str) -> tuple[str, list[str]]:
        """Extract [1], [2] style citations from answer"""
        # Regex to find [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        citations = re.findall(citation_pattern, answer)
        # Map citation numbers to context_ids
        used_context_ids = [f"ctx_{cit}" for cit in citations]
        return answer, used_context_ids
```

### 5.3 修改 dependencies.py

**目标**: 支持创建 LLM Answer Generator

**文件**: 修改 `src/ragmax/api/dependencies.py`

**变更**:
```python
def create_answer_generator(settings: Settings | None = None) -> AnswerGenerator:
    resolved_settings = settings or get_settings()
    generator = resolved_settings.retrieval_answer_generator.lower()
    
    if generator == "extractive":
        return ExtractiveAnswerGenerator(...)
    
    if generator == "llm":
        llm_client = create_llm_client(resolved_settings)
        return LLMAnswerGenerator(
            llm_client=llm_client,
            max_context_items=resolved_settings.retrieval_answer_max_context_items,
            temperature=resolved_settings.retrieval_llm_temperature,
        )
    
    raise ConfigurationError(f"Unsupported answer generator: {generator}")

def create_llm_client(settings: Settings) -> LLMClient:
    provider = settings.retrieval_llm_provider.lower()
    if provider == "openai":
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        return OpenAILLMClient(
            api_key=api_key,
            model=settings.retrieval_llm_model,
            base_url=settings.openai_base_url,
        )
    raise ConfigurationError(f"Unsupported LLM provider: {provider}")
```

### 5.4 配置项

```python
# config.py 新增
retrieval_answer_generator: str = "extractive"  # "extractive" | "llm"
retrieval_llm_provider: str = "openai"  # "openai"
retrieval_llm_model: str = "gpt-4o-mini"
retrieval_llm_temperature: float = 0.0
retrieval_llm_max_tokens: int = 1000
```

---

## 依赖更新

### pyproject.toml 新增依赖

```toml
dependencies = [
    # ... 现有依赖 ...
    "sentence-transformers>=3.0.0",  # For BGE Reranker
    "openai>=1.0.0",  # For LLM Answer Generation
]
```

---

## 数据库迁移

### 不需要新的迁移
- BM25 使用 Qdrant 稀疏向量，无需修改 PostgreSQL schema
- 所有新功能都是计算层，不涉及存储结构变更

---

## 测试策略

### 单元测试

每个新模块都需要单元测试：

1. **Query Processing**:
   - `tests/test_query_normalizer.py`
   - `tests/test_query_transformer.py`

2. **Hybrid Retrieval**:
   - `tests/test_sparse_searcher.py`
   - `tests/test_rrf_fuser.py`

3. **Reranking**:
   - `tests/test_bge_reranker.py`

4. **Context Building**:
   - `tests/test_context_builder.py`

5. **Answer Generation**:
   - `tests/test_llm_answer_generator.py` (mock LLM client)

### 集成测试

修改 `tests/test_retrieval.py` 增加完整流程测试：
- 混合搜索 + RRF
- 两阶段重排
- LLM 答案生成

---

## 实现顺序

### Milestone 1: Query Processing + Hybrid Retrieval（约 3-4 小时）
1. Query normalizer & transformer
2. Qdrant sparse searcher
3. RRF fusion
4. 修改 RetrievalService 整合

### Milestone 2: Reranking（约 2-3 小时）
5. BGE cross-encoder reranker
6. 两阶段重排流程
7. 配置和依赖注入

### Milestone 3: Context Building（约 1-2 小时）
8. Enhanced context builder
9. Deduplication

### Milestone 4: Answer Generation（约 2-3 小时）
10. LLM client 接口
11. LLM answer generator
12. Prompt engineering

### Milestone 5: Testing & Integration（约 2-3 小时）
13. 单元测试
14. 集成测试
15. 端到端测试
16. 文档更新

**总计**: 约 10-15 小时

---

## 风险与注意事项

### 技术风险
1. **BGE Reranker 模型下载**: 首次运行需要下载 ~500MB 模型
   - 解决: 提供预下载脚本或使用 HuggingFace cache
   
2. **LLM API 成本**: OpenAI API 按 token 计费
   - 解决: 配置 max_tokens 限制，提供 extractive fallback

3. **Qdrant 稀疏向量支持**: 需要 Qdrant v1.10+
   - 解决: 更新 docker-compose.yml 中的 Qdrant 版本

### 向后兼容性
- 所有新功能默认禁用，需要显式配置
- 现有 API 行为不变
- 配置文件向后兼容

### 性能考虑
- Cross-encoder 推理较慢 (~50-100ms for 100 pairs)
  - 解决: 粗排先降低候选数量
- LLM 调用延迟 (~1-3s)
  - 解决: 提供 streaming 支持（后续优化）

---

## 成功标准

1. ✅ 所有 Phase 1-5 功能实现完成
2. ✅ 单元测试覆盖率 > 80%
3. ✅ 集成测试通过
4. ✅ 配置文件完整，支持各种组合
5. ✅ 依赖注入正确，可替换各组件
6. ✅ 向后兼容，不破坏现有功能
7. ✅ 文档更新（README, .env.example）
