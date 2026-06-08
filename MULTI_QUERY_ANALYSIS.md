# Multi-Query 实现分析与优化建议

## 当前实现分析

### 1. 实现位置

**核心文件**: `src/ragmax/infrastructure/retrieval/query/transformer.py`

**类**: `MultiQueryTransformer`

### 2. 当前实现逻辑

```python
class MultiQueryTransformer:
    """Multi-query transformer that generates multiple query variants."""
    
    def __init__(self, llm_client: LLMClient, num_variants: int = 3):
        self.llm = llm_client
        self.num_variants = max(1, num_variants)
    
    async def transform(self, query: NormalizedQuery, strategy: str = "multi_query") -> TransformedQuery:
        # 1. 构建 Prompt
        system_prompt = (
            "You are an expert at rephrasing questions. "
            f"Generate {self.num_variants} different ways to ask the same question. "
            "Each variant should capture the same intent but use different wording. "
            f"Return exactly {self.num_variants} variants, one per line, numbered."
        )
        
        # 2. 调用 LLM 生成变体
        response = await self.llm.generate(messages, temperature=0.5, max_tokens=300)
        
        # 3. 解析变体（去除编号）
        variants = self._parse_variants(response.content)
        
        # 4. 包含原始查询作为第一个变体
        all_variants = (query.normalized,) + variants
        
        return TransformedQuery(
            original=query.normalized,
            variants=all_variants,  # (原始查询, 变体1, 变体2, 变体3)
            strategy="multi_query",
            metadata={"model": ..., "usage": ..., "generated_count": len(variants)}
        )
```

### 3. 检索流程集成

**位置**: `src/ragmax/application/retrieval/service.py`

```python
async def _vector_search_with_variants(self, transformed_query, command, top_k):
    """对每个查询变体执行向量搜索"""
    all_hits = []
    seen_node_ids = set()
    
    # 遍历所有查询变体
    for variant in transformed_query.variants:  # 例如: 4 个变体
        query_vector = await self._embedding_provider.embed_texts([variant])
        hits = await self._vector_searcher.search(...)  # 每个变体检索 top_k
        
        # 去重合并
        for hit in hits:
            if hit.node_id not in seen_node_ids:
                all_hits.append(hit)
                seen_node_ids.add(hit.node_id)
    
    # 按分数排序，返回 top_k
    all_hits.sort(key=lambda x: x.score, reverse=True)
    return tuple(all_hits[:top_k])

async def _bm25_search_with_variants(self, transformed_query, command, top_k):
    """对每个查询变体执行 BM25 搜索（同样逻辑）"""
    # 同样的去重合并逻辑
```

### 4. 实现深度评估

| 维度 | 实现情况 | 完成度 |
|------|---------|--------|
| **LLM 生成变体** | ✅ 完整实现 | 100% |
| **变体解析** | ✅ 支持多种编号格式 | 100% |
| **多变体检索** | ✅ 对每个变体独立检索 | 100% |
| **结果去重** | ✅ 按 node_id 去重 | 100% |
| **结果合并** | ✅ 按分数排序后取 top_k | 100% |
| **支持 Vector Search** | ✅ 完整支持 | 100% |
| **支持 BM25 Search** | ✅ 完整支持 | 100% |
| **Metadata 追踪** | ✅ 记录模型、token 使用 | 100% |

**结论**: Multi-Query 实现已经非常完整，达到了 **生产级别**。

---

## 当前问题与优化方向

### 问题 1: 使用了大模型（成本高、延迟高）

**当前实现**:
```python
# 使用 OpenAI API (gpt-4o-mini 或 gpt-4)
llm_client = OpenAILLMClient(api_key=..., model="gpt-4o-mini")
multi_query_transformer = MultiQueryTransformer(llm_client, num_variants=3)
```

**问题**:
- 每次查询都调用 OpenAI API
- 延迟: ~300-800ms
- 成本: 每次查询约 $0.0001-0.0003
- 依赖外部服务

**优化建议**: 使用本地小模型

---

## 优化方案：使用小模型替代

### 方案 1: 本地小模型（推荐）

#### 1.1 使用 Qwen2.5-1.5B-Instruct

**优势**:
- 模型大小: ~3GB
- 推理速度: ~100-200ms (CPU), ~20-50ms (GPU)
- 免费、无外部依赖
- 中英文支持优秀

**实现**:

```python
# src/ragmax/infrastructure/llm/local_client.py

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class LocalLLMClient:
    """Local small model client for query transformation."""
    
    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
        device: str = "cpu",
        max_memory_gb: int = 4,
    ):
        """Initialize local LLM client.
        
        Args:
            model_name: HuggingFace model name
            device: "cpu" or "cuda"
            max_memory_gb: Max memory to use (for quantization)
        """
        self.device = device
        self.model_name = model_name
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Load model with quantization for memory efficiency
        if max_memory_gb <= 4:
            # 4-bit quantization for low memory
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                load_in_4bit=True,
                device_map="auto",
            )
        else:
            # Full precision
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map=device,
            )
        
        self.model.eval()
    
    async def generate(
        self,
        messages: list,
        temperature: float = 0.5,
        max_tokens: int = 300,
    ):
        """Generate completion from messages."""
        # Convert messages to chat format
        prompt = self._format_chat(messages)
        
        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode
        generated_text = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        
        return LLMResponse(
            content=generated_text,
            usage={
                "prompt_tokens": inputs.input_ids.shape[1],
                "completion_tokens": outputs.shape[1] - inputs.input_ids.shape[1],
                "total_tokens": outputs.shape[1],
            },
            model=self.model_name,
        )
    
    def _format_chat(self, messages: list) -> str:
        """Format messages into Qwen chat format."""
        formatted = ""
        for msg in messages:
            if msg.role == "system":
                formatted += f"<|im_start|>system\n{msg.content}<|im_end|>\n"
            elif msg.role == "user":
                formatted += f"<|im_start|>user\n{msg.content}<|im_end|>\n"
        formatted += "<|im_start|>assistant\n"
        return formatted
```

#### 1.2 配置集成

```python
# src/ragmax/core/config.py

class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # LLM Provider
    retrieval_llm_provider: str = "openai"  # "openai" | "local"
    
    # Local LLM Config
    retrieval_local_llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    retrieval_local_llm_device: str = "cpu"
    retrieval_local_llm_max_memory_gb: int = 4
```

```python
# src/ragmax/api/dependencies.py

def create_llm_client(settings: Settings) -> LLMClient:
    """Create LLM client for answer generation."""
    provider = settings.retrieval_llm_provider.lower()
    
    if provider == "openai":
        from ragmax.infrastructure.llm.client import OpenAILLMClient
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        return OpenAILLMClient(
            api_key=api_key,
            model=settings.retrieval_llm_model,
            base_url=settings.openai_base_url,
        )
    
    if provider == "local":
        from ragmax.infrastructure.llm.local_client import LocalLLMClient
        return LocalLLMClient(
            model_name=settings.retrieval_local_llm_model,
            device=settings.retrieval_local_llm_device,
            max_memory_gb=settings.retrieval_local_llm_max_memory_gb,
        )
    
    raise ConfigurationError(f"Unsupported LLM provider: {provider}")
```

#### 1.3 使用示例

```env
# .env

# 使用本地小模型
RETRIEVAL_LLM_PROVIDER=local
RETRIEVAL_LOCAL_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
RETRIEVAL_LOCAL_LLM_DEVICE=cpu  # 或 cuda
RETRIEVAL_LOCAL_LLM_MAX_MEMORY_GB=4

# Query Transformation
RETRIEVAL_QUERY_TRANSFORMATION=multi_query
RETRIEVAL_QUERY_MULTI_QUERY_COUNT=3
```

---

### 方案 2: 专用查询扩展模型

#### 2.1 使用 doc2query 模型

**模型**: `BeIR/query-gen-msmarco-t5-base-v1`

**优势**:
- 专门训练用于查询生成
- 模型小 (~220MB)
- 速度快 (~50-100ms)

**实现**:

```python
# src/ragmax/infrastructure/retrieval/query/doc2query_transformer.py

from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch

class Doc2QueryTransformer:
    """Specialized query expansion using doc2query model."""
    
    def __init__(
        self,
        model_name: str = "BeIR/query-gen-msmarco-t5-base-v1",
        device: str = "cpu",
        num_variants: int = 3,
    ):
        self.device = device
        self.num_variants = num_variants
        
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name).to(device)
        self.model.eval()
    
    async def transform(self, query: NormalizedQuery, strategy: str = "doc2query") -> TransformedQuery:
        """Generate query variants using doc2query model."""
        
        # Prepare input
        input_text = f"Generate diverse queries for: {query.normalized}"
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True).to(self.device)
        
        # Generate variants with diverse sampling
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=100,
                num_return_sequences=self.num_variants,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=0.8,
            )
        
        # Decode variants
        variants = []
        for output in outputs:
            variant = self.tokenizer.decode(output, skip_special_tokens=True)
            if variant and variant != query.normalized:
                variants.append(variant)
        
        # Include original query
        all_variants = (query.normalized,) + tuple(variants[:self.num_variants])
        
        return TransformedQuery(
            original=query.normalized,
            variants=all_variants,
            strategy="doc2query",
            metadata={"generated_count": len(variants)},
        )
```

---

### 方案 3: 规则 + 模板（零成本）

对于简单场景，可以使用规则方法：

```python
# src/ragmax/infrastructure/retrieval/query/template_transformer.py

class TemplateQueryTransformer:
    """Template-based query expansion (no LLM needed)."""
    
    TEMPLATES = [
        "What is {query}?",
        "How does {query} work?",
        "Explain {query}",
        "Tell me about {query}",
        "{query} definition",
        "{query} explanation",
    ]
    
    def __init__(self, num_variants: int = 3):
        self.num_variants = num_variants
    
    async def transform(self, query: NormalizedQuery, strategy: str = "template") -> TransformedQuery:
        """Generate query variants using templates."""
        
        # Generate variants from templates
        variants = []
        for template in self.TEMPLATES[:self.num_variants]:
            variant = template.format(query=query.normalized)
            if variant != query.normalized:
                variants.append(variant)
        
        all_variants = (query.normalized,) + tuple(variants)
        
        return TransformedQuery(
            original=query.normalized,
            variants=all_variants,
            strategy="template",
            metadata={"method": "template_based"},
        )
```

---

## 性能对比

| 方案 | 模型大小 | 延迟 (CPU) | 延迟 (GPU) | 成本 | 质量 |
|------|---------|-----------|-----------|------|------|
| **OpenAI API** (当前) | N/A | 300-800ms | N/A | $0.0001/query | ⭐⭐⭐⭐⭐ |
| **Qwen2.5-1.5B** | 3GB | 100-200ms | 20-50ms | $0 | ⭐⭐⭐⭐ |
| **Doc2Query T5** | 220MB | 50-100ms | 10-30ms | $0 | ⭐⭐⭐ |
| **Template** | 0 | <1ms | <1ms | $0 | ⭐⭐ |

---

## 推荐方案

### 推荐 1: Qwen2.5-1.5B（平衡方案）

**适用场景**: 大多数生产环境

**优势**:
- 质量接近 OpenAI
- 延迟可接受
- 免费、可控
- 支持中英文

**配置**:
```env
RETRIEVAL_LLM_PROVIDER=local
RETRIEVAL_LOCAL_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
RETRIEVAL_LOCAL_LLM_DEVICE=cpu
```

### 推荐 2: Doc2Query（高性能场景）

**适用场景**: 对延迟敏感的场景

**优势**:
- 极小模型
- 极快速度
- 专用任务优化

**配置**:
```env
RETRIEVAL_QUERY_TRANSFORMATION=doc2query
```

### 推荐 3: 混合策略

根据查询复杂度选择：
- 简单查询 → Template
- 中等查询 → Doc2Query
- 复杂查询 → Qwen2.5

---

## 实现优先级

### Phase 1: 添加本地 LLM 支持（高优先级）

1. ✅ 实现 `LocalLLMClient`
2. ✅ 更新 `create_llm_client()` 工厂函数
3. ✅ 添加配置项
4. ✅ 文档和使用示例

**预计工作量**: 2-3 小时

### Phase 2: 添加 Doc2Query 支持（中优先级）

1. ✅ 实现 `Doc2QueryTransformer`
2. ✅ 集成到 transformer 工厂
3. ✅ 性能测试

**预计工作量**: 1-2 小时

### Phase 3: 添加 Template 方法（低优先级）

1. ✅ 实现 `TemplateQueryTransformer`
2. ✅ 作为 fallback 选项

**预计工作量**: 0.5-1 小时

---

## 依赖更新

```toml
# pyproject.toml

dependencies = [
    # ... 现有依赖 ...
    "transformers>=4.30.0",  # For local LLM and Doc2Query
    "torch>=2.0.0",  # For model inference
    "accelerate>=0.20.0",  # For model loading optimization
    "bitsandbytes>=0.40.0",  # For quantization (optional, for low memory)
]
```

---

## 总结

### 当前 Multi-Query 实现

✅ **功能完整度**: 100% - 生产级别实现
✅ **架构设计**: 优秀 - 模块化、可扩展
✅ **代码质量**: 高 - 清晰、可维护

### 主要改进点

⚠️ **成本优化**: 替换 OpenAI API 为本地模型
⚠️ **延迟优化**: 使用小模型降低延迟
⚠️ **灵活性**: 支持多种生成策略

### 推荐行动

1. **立即**: 实现 LocalLLMClient (Qwen2.5-1.5B)
2. **短期**: 添加 Doc2Query 支持
3. **长期**: 根据实际使用数据优化策略选择
