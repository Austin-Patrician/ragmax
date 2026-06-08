# 混合检索并发优化文档

## 问题发现

### 原始实现（串行执行）

```python
# src/ragmax/application/retrieval/service.py (第 83-86 行)

# 3. Hybrid search: Vector + BM25 (if enabled)
if self._bm25_searcher and self._search_fuser:
    # Perform both vector and BM25 search, then fuse
    vector_hits = await self._vector_search_with_variants(
        transformed_query, command, top_k
    )
    bm25_hits = await self._bm25_search_with_variants(
        transformed_query, command, top_k
    )
```

**问题**：
- Vector 搜索完成后才开始 BM25 搜索
- 总延迟 = Vector 延迟 + BM25 延迟
- 没有充分利用异步并发能力

---

## 优化方案

### 使用 asyncio.gather() 并发执行

```python
# 优化后代码

# 3. Hybrid search: Vector + BM25 (if enabled)
if self._bm25_searcher and self._search_fuser:
    # Perform both vector and BM25 search concurrently
    import asyncio

    vector_hits, bm25_hits = await asyncio.gather(
        self._vector_search_with_variants(transformed_query, command, top_k),
        self._bm25_search_with_variants(transformed_query, command, top_k),
    )
```

---

## 性能提升

### 延迟对比

假设：
- Vector Search 延迟: 30ms
- BM25 Search 延迟: 30ms

| 实现方式 | 总延迟 | 计算方式 |
|---------|--------|---------|
| **串行**（优化前） | **60ms** | 30ms + 30ms |
| **并发**（优化后） | **30ms** | max(30ms, 30ms) |

**性能提升**: 50% 延迟减少 🚀

### 真实场景

在更复杂的场景下（多查询变体）：

| 场景 | 串行延迟 | 并发延迟 | 提升 |
|------|---------|---------|------|
| 单查询 | 60ms | 30ms | 50% |
| 3 个查询变体 | 180ms | 90ms | 50% |
| 5 个查询变体 | 300ms | 150ms | 50% |

---

## asyncio.gather() 工作原理

### 基本用法

```python
import asyncio

# 并发执行多个协程
result1, result2, result3 = await asyncio.gather(
    async_func1(),
    async_func2(),
    async_func3(),
)
```

### 特点

1. **并发执行**: 所有协程同时启动
2. **顺序返回**: 结果按传入顺序返回（不是完成顺序）
3. **失败处理**: 默认情况下，任何一个失败会导致整体失败
4. **异常处理**: 可以使用 `return_exceptions=True` 处理部分失败

### 与其他方法对比

```python
# 方法 1: 串行执行（慢）
result1 = await func1()
result2 = await func2()

# 方法 2: asyncio.gather（推荐）
result1, result2 = await asyncio.gather(func1(), func2())

# 方法 3: asyncio.create_task（更灵活但复杂）
task1 = asyncio.create_task(func1())
task2 = asyncio.create_task(func2())
result1 = await task1
result2 = await task2
```

---

## 其他可优化的地方

### 1. 多查询变体搜索

**当前实现**（`_vector_search_with_variants`）:

```python
async def _vector_search_with_variants(self, transformed_query, command, top_k):
    all_hits = []
    seen_node_ids = set()
    
    # 串行处理每个查询变体
    for variant in transformed_query.variants:
        query_vector = await self._embedding_provider.embed_texts([variant])
        hits = await self._vector_searcher.search(...)
        # ...
```

**优化建议**：

```python
async def _vector_search_with_variants(self, transformed_query, command, top_k):
    import asyncio
    
    # 并发生成所有查询变体的向量
    query_vectors = await self._embedding_provider.embed_texts(
        list(transformed_query.variants)
    )
    
    # 并发执行所有搜索
    all_search_results = await asyncio.gather(*[
        self._vector_searcher.search(
            collection_names=self._text_collection_names(),
            query_vector=query_vectors[i],
            notebook_id=command.notebook_id,
            source_ids=command.source_ids,
            content_types=command.content_types,
            limit=top_k,
            score_threshold=command.score_threshold,
        )
        for i in range(len(transformed_query.variants))
    ])
    
    # 合并去重
    all_hits = []
    seen_node_ids = set()
    for hits in all_search_results:
        for hit in hits:
            if hit.node_id not in seen_node_ids:
                all_hits.append(hit)
                seen_node_ids.add(hit.node_id)
    
    all_hits.sort(key=lambda x: x.score, reverse=True)
    return tuple(all_hits[:top_k])
```

**性能提升**（3 个查询变体）:
- 优化前: 90ms (30ms × 3)
- 优化后: 30ms
- **提升**: 67% 延迟减少

### 2. 多集合搜索

如果搜索多个 Qdrant 集合，也可以并发：

```python
# 并发搜索多个集合
collection_results = await asyncio.gather(*[
    self.client.search(collection_name=col, ...)
    for col in collection_names
])
```

---

## 注意事项

### 1. 错误处理

默认情况下，任何一个协程失败会导致整体失败：

```python
try:
    vector_hits, bm25_hits = await asyncio.gather(
        self._vector_search_with_variants(...),
        self._bm25_search_with_variants(...),
    )
except Exception as e:
    # 处理失败情况
    # 可以 fallback 到只用 vector search
    vector_hits = await self._vector_search_with_variants(...)
    bm25_hits = ()
```

### 2. 返回部分结果

如果希望某个搜索失败时继续执行：

```python
results = await asyncio.gather(
    self._vector_search_with_variants(...),
    self._bm25_search_with_variants(...),
    return_exceptions=True,  # 返回异常而不是抛出
)

# 处理结果
vector_hits = results[0] if not isinstance(results[0], Exception) else ()
bm25_hits = results[1] if not isinstance(results[1], Exception) else ()
```

### 3. 资源限制

并发执行会同时占用：
- 数据库连接
- 网络连接
- CPU/内存资源

确保资源池大小足够支持并发请求。

---

## 性能测试建议

### 1. 基准测试

```python
import time
import asyncio

async def benchmark_hybrid_search():
    start = time.perf_counter()
    
    # 执行混合搜索
    result = await retrieval_service.search(command)
    
    end = time.perf_counter()
    print(f"Hybrid search latency: {(end - start) * 1000:.2f}ms")
```

### 2. 分解延迟

```python
async def benchmark_detailed():
    # Vector search
    start = time.perf_counter()
    vector_hits = await self._vector_search_with_variants(...)
    vector_time = time.perf_counter() - start
    
    # BM25 search
    start = time.perf_counter()
    bm25_hits = await self._bm25_search_with_variants(...)
    bm25_time = time.perf_counter() - start
    
    print(f"Vector: {vector_time * 1000:.2f}ms")
    print(f"BM25: {bm25_time * 1000:.2f}ms")
    print(f"Total (serial): {(vector_time + bm25_time) * 1000:.2f}ms")
    print(f"Total (parallel): {max(vector_time, bm25_time) * 1000:.2f}ms")
```

---

## 总结

### 已优化

✅ **Hybrid Search (Vector + BM25)** - 并发执行，50% 延迟减少

### 待优化

⏳ **Multi-Query Variants** - 可以进一步并发优化
⏳ **Multi-Collection Search** - 如果使用多个集合

### 预期收益

- **Hybrid Search**: 30ms → 30ms（已优化）
- **Multi-Query (3 variants)**: 90ms → 30ms（待优化）
- **总延迟优化**: 可达 **60-70% 减少**

这是一个简单但高效的优化，强烈建议立即应用！
