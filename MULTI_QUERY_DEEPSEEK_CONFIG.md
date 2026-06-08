# Multi-Query LLM 独立配置说明

## 为什么需要独立配置？

Multi-Query 查询转换和最终的 Answer Generation 有不同的需求：

### Multi-Query（查询转换）
- **任务简单**：生成 3-5 个查询变体
- **质量要求**：中等即可
- **调用频率**：每次检索 1 次
- **成本敏感**：高频调用，成本累积快
- **推荐模型**：DeepSeek V3 ($0.14/1M tokens)

### Answer Generation（答案生成）
- **任务复杂**：理解上下文、生成准确答案
- **质量要求**：高
- **调用频率**：每次答案生成 1 次
- **成本可接受**：相对低频
- **推荐模型**：GPT-4o-mini 或更强模型

---

## DeepSeek V3 配置示例

### 方案 1：使用 DeepSeek V3 for Multi-Query + GPT-4o-mini for Answer

```env
# Multi-Query Transformation (使用 DeepSeek V3 - 超高性价比)
RETRIEVAL_QUERY_TRANSFORMATION=multi_query
RETRIEVAL_QUERY_MULTI_QUERY_COUNT=3
RETRIEVAL_QUERY_LLM_PROVIDER=openai
RETRIEVAL_QUERY_LLM_MODEL=deepseek-chat
RETRIEVAL_QUERY_LLM_BASE_URL=https://api.deepseek.com/v1
RETRIEVAL_QUERY_LLM_API_KEY=sk-deepseek-xxxxxxxx

# Answer Generation (使用 GPT-4o-mini - 质量优先)
RETRIEVAL_ANSWER_GENERATOR=llm
RETRIEVAL_LLM_PROVIDER=openai
RETRIEVAL_LLM_MODEL=gpt-4o-mini
RETRIEVAL_LLM_BASE_URL=
RETRIEVAL_LLM_API_KEY=
# 如果不设置 RETRIEVAL_LLM_API_KEY，会 fallback 到 OPENAI_API_KEY
```

### 方案 2：全部使用 DeepSeek V3（极致性价比）

```env
# Multi-Query Transformation
RETRIEVAL_QUERY_TRANSFORMATION=multi_query
RETRIEVAL_QUERY_LLM_PROVIDER=openai
RETRIEVAL_QUERY_LLM_MODEL=deepseek-chat
RETRIEVAL_QUERY_LLM_BASE_URL=https://api.deepseek.com/v1
RETRIEVAL_QUERY_LLM_API_KEY=sk-deepseek-xxxxxxxx

# Answer Generation (也使用 DeepSeek)
RETRIEVAL_ANSWER_GENERATOR=llm
RETRIEVAL_LLM_PROVIDER=openai
RETRIEVAL_LLM_MODEL=deepseek-chat
RETRIEVAL_LLM_BASE_URL=https://api.deepseek.com/v1
RETRIEVAL_LLM_API_KEY=sk-deepseek-xxxxxxxx
```

### 方案 3：混合策略（推荐）

```env
# Multi-Query: DeepSeek V3 (快速、便宜)
RETRIEVAL_QUERY_TRANSFORMATION=multi_query
RETRIEVAL_QUERY_LLM_PROVIDER=openai
RETRIEVAL_QUERY_LLM_MODEL=deepseek-chat
RETRIEVAL_QUERY_LLM_BASE_URL=https://api.deepseek.com/v1
RETRIEVAL_QUERY_LLM_API_KEY=sk-deepseek-xxxxxxxx

# HyDE: GPT-4o-mini (生成假设文档需要更高质量)
# 当 RETRIEVAL_QUERY_TRANSFORMATION=hyde 时，仍使用上面的配置

# Answer Generation: GPT-4o (最高质量)
RETRIEVAL_ANSWER_GENERATOR=llm
RETRIEVAL_LLM_PROVIDER=openai
RETRIEVAL_LLM_MODEL=gpt-4o
RETRIEVAL_LLM_API_KEY=sk-openai-xxxxxxxx
```

---

## 成本对比

### Multi-Query 成本（每次查询）

假设查询 50 tokens，生成 150 tokens（3 个变体）：

| 模型 | Input | Output | 总成本 |
|------|-------|--------|--------|
| GPT-4o-mini | $0.150/1M | $0.600/1M | **$0.000102** |
| GPT-4o | $2.50/1M | $10.0/1M | **$0.001625** |
| DeepSeek V3 | $0.14/1M | $0.28/1M | **$0.000049** |

**节省比例**：
- DeepSeek vs GPT-4o-mini: **52% 节省**
- DeepSeek vs GPT-4o: **97% 节省**

### 每日 10,000 次查询的成本

| 模型 | 每日成本 | 每月成本 |
|------|---------|---------|
| GPT-4o-mini | $1.02 | $30.6 |
| GPT-4o | $16.25 | $487.5 |
| **DeepSeek V3** | **$0.49** | **$14.7** |

---

## DeepSeek V3 特点

### 优势
- ✅ **超低成本**：$0.14/1M input, $0.28/1M output
- ✅ **高性能**：性能接近 GPT-4o
- ✅ **低延迟**：API 响应快
- ✅ **中文优秀**：对中文支持极好
- ✅ **兼容 OpenAI API**：无缝切换

### 适用场景
- ✅ Multi-Query 查询扩展
- ✅ Query Rewriting
- ✅ 简单的文本生成
- ⚠️ 复杂推理任务（建议用 GPT-4o）

---

## API Key 优先级

### Multi-Query Transformation
```
RETRIEVAL_QUERY_LLM_API_KEY > OPENAI_API_KEY
RETRIEVAL_QUERY_LLM_BASE_URL > OPENAI_BASE_URL
```

### Answer Generation
```
RETRIEVAL_LLM_API_KEY > OPENAI_API_KEY
RETRIEVAL_LLM_BASE_URL > OPENAI_BASE_URL
```

这样设计的好处：
1. 如果只设置 `OPENAI_API_KEY`，两个功能都使用同一个 key
2. 如果设置了专用 key，就使用专用配置
3. 灵活性最大化

---

## 获取 DeepSeek API Key

1. 访问：https://platform.deepseek.com/
2. 注册账号
3. 进入 API Keys 页面
4. 创建新的 API Key
5. 复制到 `.env` 文件

**新用户福利**：注册通常赠送免费额度

---

## 测试配置

```bash
# 测试 DeepSeek API 连接
curl https://api.deepseek.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $RETRIEVAL_QUERY_LLM_API_KEY" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

---

## 推荐配置

```env
# ============================================
# Multi-Query: DeepSeek V3 (性价比之选)
# ============================================
RETRIEVAL_ENABLED=true
RETRIEVAL_QUERY_TRANSFORMATION=multi_query
RETRIEVAL_QUERY_MULTI_QUERY_COUNT=3

RETRIEVAL_QUERY_LLM_PROVIDER=openai
RETRIEVAL_QUERY_LLM_MODEL=deepseek-chat
RETRIEVAL_QUERY_LLM_BASE_URL=https://api.deepseek.com/v1
RETRIEVAL_QUERY_LLM_API_KEY=sk-deepseek-xxxxxxxx

# ============================================
# Answer Generation: GPT-4o-mini (质量保证)
# ============================================
RETRIEVAL_ANSWER_GENERATOR=llm
RETRIEVAL_LLM_PROVIDER=openai
RETRIEVAL_LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-openai-xxxxxxxx
```

这个配置平衡了成本和质量，是大多数生产环境的最佳选择！
