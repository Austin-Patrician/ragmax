# RAGMax 观测评估平台设计

## 1. 设计目标

构建一个类似 [deepeval](https://github.com/confident-ai/deepeval) 的 RAG 评估观测平台，用于：

- **参数调优**: 对比不同配置（embedding 模型、rerank 策略、LLM 等）的效果
- **回归测试**: 确保系统变更不会降低质量
- **持续优化**: 基于量化指标迭代改进检索和生成质量
- **问题诊断**: 快速定位 pipeline 中的瓶颈环节

## 2. 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Evaluation Platform                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Test Cases  │  │   Metrics    │  │  Experiments │      │
│  │  Management  │  │   Engine     │  │   Tracking   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Synthetic   │  │  Comparison  │  │   Reports &  │      │
│  │ Data Gen     │  │    UI        │  │   Dashboard  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 3. 评估指标体系

基于 [RAG 评估最佳实践](https://www.confident-ai.com/blog/rag-evaluation-metrics-answer-relevancy-faithfulness-and-more)，设计三层指标：

### 3.1 检索层指标 (Retrieval Metrics)

| 指标 | 定义 | 计算方式 | 目标值 |
|------|------|---------|--------|
| **Context Precision** | 检索结果中相关文档的比例 | relevant_docs / total_retrieved | ≥ 0.8 |
| **Context Recall** | 所有相关文档中被检索到的比例 | retrieved_relevant / all_relevant | ≥ 0.9 |
| **MRR (Mean Reciprocal Rank)** | 首个相关文档的排名倒数 | 1 / rank_of_first_relevant | ≥ 0.7 |
| **NDCG@K** | 考虑排序质量的归一化折损累积增益 | DCG@K / IDCG@K | ≥ 0.75 |
| **Retrieval Latency** | 检索延迟（P50/P95/P99） | 毫秒 | P95 < 100ms |

### 3.2 生成层指标 (Generation Metrics)

| 指标 | 定义 | 计算方式 | 目标值 |
|------|------|---------|--------|
| **Faithfulness** | 答案中每个陈述是否有上下文支持 | supported_claims / total_claims | ≥ 0.95 |
| **Answer Relevancy** | 答案与问题的相关性 | LLM-as-Judge 打分 | ≥ 0.85 |
| **Correctness** | 答案与参考答案的一致性 | ROUGE-L / BERTScore / LLM Judge | ≥ 0.8 |
| **Citation Accuracy** | 引用标注的准确性 | correct_citations / total_citations | ≥ 0.9 |
| **Hallucination Rate** | 无依据陈述的比例 | unsupported_claims / total_claims | ≤ 0.05 |

### 3.3 端到端指标 (E2E Metrics)

| 指标 | 定义 | 目标值 |
|------|------|--------|
| **Overall Quality Score** | 综合评分（加权平均） | ≥ 0.85 |
| **End-to-End Latency** | 从用户提问到返回答案的总时间（P95） | < 2s |
| **Token Cost** | 每次查询的 token 消耗成本 | < $0.01 |
| **User Satisfaction** | 用户反馈满意度（thumbs up/down） | ≥ 90% |

## 4. 数据模型设计

### 4.1 测试用例 (TestCase)

```python
@dataclass
class EvalTestCase:
    """单个评估测试用例"""
    id: str
    question: str                      # 用户问题
    expected_answer: str | None        # 参考答案（可选）
    ground_truth_docs: list[str]       # 相关文档 ID 列表
    metadata: dict[str, Any]           # 标签、难度、领域等
    created_at: datetime
    
@dataclass
class TestDataset:
    """测试数据集"""
    id: str
    name: str                          # 数据集名称
    description: str
    test_cases: list[EvalTestCase]
    version: str
    created_at: datetime
```

### 4.2 实验运行 (ExperimentRun)

```python
@dataclass
class ExperimentConfig:
    """实验配置（可序列化为 JSON）"""
    # Retrieval 配置
    embedding_model: str
    top_k: int
    enable_bm25: bool
    enable_rerank: bool
    rerank_model: str | None
    rerank_top_n: int | None
    fusion_strategy: str               # "rrf", "linear", "weighted"
    
    # Query Transform 配置
    query_strategy: str                # "original", "hyde", "multi_query"
    multi_query_llm: str | None
    
    # Generation 配置
    answer_llm: str
    temperature: float
    max_tokens: int

@dataclass
class ExperimentRun:
    """单次实验运行"""
    id: str
    name: str
    dataset_id: str
    config: ExperimentConfig
    results: list[EvalResult]
    metrics_summary: MetricsSummary
    status: str                        # "running", "completed", "failed"
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None
```

### 4.3 评估结果 (EvalResult)

```python
@dataclass
class RetrievalResult:
    """检索阶段结果"""
    retrieved_doc_ids: list[str]
    scores: list[float]
    latency_ms: float
    
@dataclass
class GenerationResult:
    """生成阶段结果"""
    answer: str
    citations: list[int]
    latency_ms: float
    token_count: int

@dataclass
class EvalResult:
    """单个测试用例的评估结果"""
    test_case_id: str
    retrieval: RetrievalResult
    generation: GenerationResult
    metrics: dict[str, float]          # 指标名 -> 分数
    passed: bool
    error: str | None

@dataclass
class MetricsSummary:
    """整体指标汇总"""
    # 检索层
    context_precision: float
    context_recall: float
    mrr: float
    ndcg_at_k: float
    retrieval_latency_p95: float
    
    # 生成层
    faithfulness: float
    answer_relevancy: float
    correctness: float
    citation_accuracy: float
    hallucination_rate: float
    
    # 端到端
    overall_score: float
    e2e_latency_p95: float
    avg_token_cost: float
    pass_rate: float                   # 通过测试的比例
```

## 5. 指标计算引擎

### 5.1 接口设计

```python
from abc import ABC, abstractmethod

class Metric(ABC):
    """指标计算基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """指标名称"""
        pass
    
    @property
    @abstractmethod
    def requires_llm(self) -> bool:
        """是否需要 LLM 评估"""
        pass
    
    @abstractmethod
    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        """计算指标分数 (0-1)"""
        pass
    
    @property
    def threshold(self) -> float:
        """通过阈值"""
        return 0.7
```

### 5.2 检索指标实现示例

```python
class ContextPrecisionMetric(Metric):
    """上下文精确度：检索到的文档中有多少是相关的"""
    
    name = "context_precision"
    requires_llm = False
    threshold = 0.8
    
    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        ground_truth_set = set(test_case.ground_truth_docs)
        retrieved_set = set(retrieval_result.retrieved_doc_ids)
        
        if not retrieved_set:
            return 0.0
        
        relevant_retrieved = ground_truth_set & retrieved_set
        return len(relevant_retrieved) / len(retrieved_set)

class ContextRecallMetric(Metric):
    """上下文召回率：相关文档中有多少被检索到"""
    
    name = "context_recall"
    requires_llm = False
    threshold = 0.9
    
    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        ground_truth_set = set(test_case.ground_truth_docs)
        retrieved_set = set(retrieval_result.retrieved_doc_ids)
        
        if not ground_truth_set:
            return 1.0  # 没有 ground truth，无法评估
        
        relevant_retrieved = ground_truth_set & retrieved_set
        return len(relevant_retrieved) / len(ground_truth_set)
```

### 5.3 生成指标实现示例

```python
class FaithfulnessMetric(Metric):
    """忠实度：答案中的陈述是否有上下文支持（使用 LLM 评估）"""
    
    name = "faithfulness"
    requires_llm = True
    threshold = 0.95
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        # 1. 提取答案中的陈述（claims）
        claims = await self._extract_claims(generation_result.answer)
        
        if not claims:
            return 1.0
        
        # 2. 检查每个陈述是否有上下文支持
        context = await self._get_context(retrieval_result.retrieved_doc_ids)
        supported_count = 0
        
        for claim in claims:
            is_supported = await self._verify_claim(claim, context)
            if is_supported:
                supported_count += 1
        
        return supported_count / len(claims)
    
    async def _extract_claims(self, answer: str) -> list[str]:
        """使用 LLM 提取答案中的独立陈述"""
        prompt = f"""分解以下答案为独立的事实陈述列表。
        
答案: {answer}

以 JSON 数组格式返回: ["陈述1", "陈述2", ...]"""
        
        response = await self.llm.generate([{"role": "user", "content": prompt}])
        # 解析 JSON
        return json.loads(response.content)
    
    async def _verify_claim(self, claim: str, context: str) -> bool:
        """使用 LLM 判断陈述是否被上下文支持"""
        prompt = f"""判断以下陈述是否被上下文支持。

上下文: {context}

陈述: {claim}

仅回答 "YES" 或 "NO"。"""
        
        response = await self.llm.generate([{"role": "user", "content": prompt}])
        return "YES" in response.content.upper()
```

## 6. 测试用例管理

### 6.1 手动创建测试集

```python
# tests/evaluation/datasets/customer_support.json
{
  "name": "Customer Support QA",
  "description": "客服场景常见问题测试集",
  "version": "1.0.0",
  "test_cases": [
    {
      "id": "cs-001",
      "question": "如何重置我的密码？",
      "expected_answer": "可以通过登录页面点击"忘记密码"链接，输入注册邮箱后会收到重置链接。",
      "ground_truth_docs": ["doc_auth_reset_password", "doc_faq_account"],
      "metadata": {
        "category": "account",
        "difficulty": "easy",
        "language": "zh"
      }
    },
    {
      "id": "cs-002",
      "question": "退款需要多久到账？",
      "expected_answer": "退款通常在 3-5 个工作日内到账，具体时间取决于支付方式。",
      "ground_truth_docs": ["doc_refund_policy"],
      "metadata": {
        "category": "payment",
        "difficulty": "medium",
        "language": "zh"
      }
    }
  ]
}
```

### 6.2 合成数据生成

```python
class SyntheticDataGenerator:
    """基于现有文档生成测试用例"""
    
    def __init__(self, llm_client: LLMClient, doc_store: DocumentStore):
        self.llm = llm_client
        self.doc_store = doc_store
    
    async def generate_qa_pairs(
        self,
        source_ids: list[str],
        num_pairs: int = 10,
        difficulty: str = "mixed",  # "easy", "medium", "hard", "mixed"
    ) -> list[EvalTestCase]:
        """从指定文档生成问答对"""
        
        tasks = []
        for source_id in source_ids:
            doc = await self.doc_store.get(source_id)
            task = self._generate_from_doc(doc, num_pairs // len(source_ids), difficulty)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return [case for batch in results for case in batch]
    
    async def _generate_from_doc(
        self,
        doc: Document,
        count: int,
        difficulty: str,
    ) -> list[EvalTestCase]:
        """从单个文档生成多个问答对"""
        
        prompt = f"""基于以下文档内容，生成 {count} 个不同难度的问答对。

文档内容:
{doc.content}

难度要求: {difficulty}

对于每个问答对：
1. 问题应该是自然的用户提问
2. 答案必须完全基于文档内容
3. 根据难度调整问题复杂度：
   - easy: 直接事实查询
   - medium: 需要理解和推理
   - hard: 需要综合多处信息

以 JSON 格式返回:
[
  {{
    "question": "...",
    "answer": "...",
    "difficulty": "easy/medium/hard"
  }}
]"""
        
        response = await self.llm.generate([{"role": "user", "content": prompt}])
        qa_pairs = json.loads(response.content)
        
        return [
            EvalTestCase(
                id=f"syn_{doc.id}_{i}",
                question=pair["question"],
                expected_answer=pair["answer"],
                ground_truth_docs=[doc.id],
                metadata={
                    "difficulty": pair["difficulty"],
                    "synthetic": True,
                    "source_doc": doc.id,
                },
                created_at=datetime.now(),
            )
            for i, pair in enumerate(qa_pairs)
        ]
```

## 7. 实验执行引擎

### 7.1 评估器核心逻辑

```python
class RAGEvaluator:
    """RAG 系统评估器"""
    
    def __init__(
        self,
        retrieval_service: RetrievalService,
        metrics: list[Metric],
        llm_client: LLMClient,
    ):
        self.retrieval_service = retrieval_service
        self.metrics = metrics
        self.llm = llm_client
    
    async def run_experiment(
        self,
        dataset: TestDataset,
        config: ExperimentConfig,
        name: str | None = None,
    ) -> ExperimentRun:
        """运行一次完整实验"""
        
        # 1. 创建实验记录
        experiment = ExperimentRun(
            id=str(uuid.uuid4()),
            name=name or f"experiment_{datetime.now().isoformat()}",
            dataset_id=dataset.id,
            config=config,
            results=[],
            metrics_summary=None,
            status="running",
            started_at=datetime.now(),
            completed_at=None,
            duration_seconds=None,
        )
        
        # 2. 应用配置到 RetrievalService
        self._apply_config(config)
        
        # 3. 并发执行所有测试用例
        tasks = [
            self._evaluate_test_case(test_case)
            for test_case in dataset.test_cases
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. 处理结果
        experiment.results = [
            r for r in results if isinstance(r, EvalResult)
        ]
        
        # 5. 计算汇总指标
        experiment.metrics_summary = self._compute_summary(experiment.results)
        
        # 6. 更新状态
        experiment.status = "completed"
        experiment.completed_at = datetime.now()
        experiment.duration_seconds = (
            experiment.completed_at - experiment.started_at
        ).total_seconds()
        
        # 7. 持久化
        await self._save_experiment(experiment)
        
        return experiment
    
    async def _evaluate_test_case(
        self,
        test_case: EvalTestCase,
    ) -> EvalResult:
        """评估单个测试用例"""
        
        try:
            # 1. 执行检索 + 生成
            start = time.time()
            retrieval_result, generation_result = await self._run_rag_pipeline(
                test_case.question
            )
            
            # 2. 计算所有指标
            metrics_scores = {}
            for metric in self.metrics:
                score = await metric.compute(
                    test_case, retrieval_result, generation_result
                )
                metrics_scores[metric.name] = score
            
            # 3. 判断是否通过
            passed = all(
                score >= metric.threshold
                for metric, score in zip(self.metrics, metrics_scores.values())
            )
            
            return EvalResult(
                test_case_id=test_case.id,
                retrieval=retrieval_result,
                generation=generation_result,
                metrics=metrics_scores,
                passed=passed,
                error=None,
            )
            
        except Exception as e:
            return EvalResult(
                test_case_id=test_case.id,
                retrieval=None,
                generation=None,
                metrics={},
                passed=False,
                error=str(e),
            )
    
    def _compute_summary(self, results: list[EvalResult]) -> MetricsSummary:
        """计算汇总指标"""
        
        # 按指标名聚合
        metric_values = defaultdict(list)
        for result in results:
            if result.error:
                continue
            for name, score in result.metrics.items():
                metric_values[name].append(score)
        
        # 计算平均值
        avg_metrics = {
            name: sum(scores) / len(scores)
            for name, scores in metric_values.items()
        }
        
        # 计算延迟分位数
        retrieval_latencies = [r.retrieval.latency_ms for r in results if r.retrieval]
        e2e_latencies = [
            r.retrieval.latency_ms + r.generation.latency_ms
            for r in results if r.retrieval and r.generation
        ]
        
        return MetricsSummary(
            context_precision=avg_metrics.get("context_precision", 0.0),
            context_recall=avg_metrics.get("context_recall", 0.0),
            mrr=avg_metrics.get("mrr", 0.0),
            ndcg_at_k=avg_metrics.get("ndcg_at_k", 0.0),
            retrieval_latency_p95=np.percentile(retrieval_latencies, 95),
            faithfulness=avg_metrics.get("faithfulness", 0.0),
            answer_relevancy=avg_metrics.get("answer_relevancy", 0.0),
            correctness=avg_metrics.get("correctness", 0.0),
            citation_accuracy=avg_metrics.get("citation_accuracy", 0.0),
            hallucination_rate=avg_metrics.get("hallucination_rate", 0.0),
            overall_score=sum(avg_metrics.values()) / len(avg_metrics),
            e2e_latency_p95=np.percentile(e2e_latencies, 95),
            avg_token_cost=self._compute_avg_cost(results),
            pass_rate=sum(r.passed for r in results) / len(results),
        )
```

## 8. 实验对比与可视化

### 8.1 对比 API

```python
class ExperimentComparison:
    """实验对比分析"""
    
    @dataclass
    class ComparisonResult:
        baseline: ExperimentRun
        candidates: list[ExperimentRun]
        metric_deltas: dict[str, list[float]]  # 指标名 -> 各候选相对基线的变化
        winner: ExperimentRun                   # 综合得分最高的
        recommendations: list[str]              # 优化建议
    
    async def compare(
        self,
        baseline_id: str,
        candidate_ids: list[str],
    ) -> ComparisonResult:
        """对比多个实验"""
        
        baseline = await self._load_experiment(baseline_id)
        candidates = [
            await self._load_experiment(cid) for cid in candidate_ids
        ]
        
        # 计算相对变化
        metric_deltas = {}
        for metric_name in baseline.metrics_summary.__annotations__:
            baseline_value = getattr(baseline.metrics_summary, metric_name)
            deltas = [
                (getattr(c.metrics_summary, metric_name) - baseline_value) / baseline_value
                for c in candidates
            ]
            metric_deltas[metric_name] = deltas
        
        # 选择最佳
        winner = max(
            [baseline] + candidates,
            key=lambda e: e.metrics_summary.overall_score
        )
        
        # 生成建议
        recommendations = self._generate_recommendations(
            baseline, candidates, metric_deltas
        )
        
        return ComparisonResult(
            baseline=baseline,
            candidates=candidates,
            metric_deltas=metric_deltas,
            winner=winner,
            recommendations=recommendations,
        )
    
    def _generate_recommendations(
        self,
        baseline: ExperimentRun,
        candidates: list[ExperimentRun],
        deltas: dict[str, list[float]],
    ) -> list[str]:
        """基于对比结果生成优化建议"""
        
        recommendations = []
        
        # 检索层分析
        if any(d > 0.1 for d in deltas.get("context_recall", [])):
            best_idx = deltas["context_recall"].index(max(deltas["context_recall"]))
            best_config = candidates[best_idx].config
            recommendations.append(
                f"提升检索召回率：使用 top_k={best_config.top_k}，"
                f"query_strategy={best_config.query_strategy}"
            )
        
        # Rerank 影响
        baseline_has_rerank = baseline.config.enable_rerank
        for i, candidate in enumerate(candidates):
            if candidate.config.enable_rerank != baseline_has_rerank:
                faithfulness_delta = deltas["faithfulness"][i]
                if faithfulness_delta > 0.05:
                    recommendations.append(
                        f"Rerank 显著提升忠实度 (+{faithfulness_delta:.1%})，建议启用"
                    )
        
        # 成本优化
        cost_deltas = deltas.get("avg_token_cost", [])
        quality_deltas = deltas.get("overall_score", [])
        for i, (cost_d, quality_d) in enumerate(zip(cost_deltas, quality_deltas)):
            if cost_d < -0.2 and quality_d > -0.05:  # 成本降低 20%+，质量下降 <5%
                config = candidates[i].config
                recommendations.append(
                    f"成本优化方案：使用 {config.answer_llm} 可节省 {-cost_d:.1%} 成本，"
                    f"质量仅下降 {-quality_d:.1%}"
                )
        
        return recommendations
```

### 8.2 CLI 工具

```bash
# 运行评估
ragmax eval run \
  --dataset customer_support_v1 \
  --config experiments/baseline.yaml \
  --name "baseline_2026_06_08"

# 对比实验
ragmax eval compare \
  --baseline exp_001 \
  --candidates exp_002 exp_003 exp_004 \
  --output comparison_report.html

# 查看排行榜
ragmax eval leaderboard --dataset customer_support_v1

# 生成测试集
ragmax eval generate-dataset \
  --source-ids doc1,doc2,doc3 \
  --num-cases 50 \
  --output datasets/synthetic_v1.json
```

### 8.3 Dashboard UI (React + Recharts)

**关键页面**:

1. **概览页** (Overview)
   - 最近实验趋势图（Overall Score 变化）
   - 关键指标卡片（Faithfulness, Context Recall, Latency, Cost）
   - 快速操作入口

2. **实验详情** (Experiment Detail)
   - 配置摘要
   - 指标雷达图
   - 失败用例列表（可点击查看详情）
   - 延迟分布直方图
   - 成本分解饼图

3. **对比视图** (Comparison)
   - 并排配置对比表
   - 指标差异热力图
   - 案例级别对比（哪些变好/变坏）
   - AI 生成的优化建议

4. **测试集管理** (Datasets)
   - 数据集列表
   - 用例编辑器
   - 标注工具（标记 ground truth）
   - 合成数据生成器

## 9. 持久化与存储

### 9.1 数据库 Schema

```sql
-- 测试数据集
CREATE TABLE eval_datasets (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, version)
);

-- 测试用例
CREATE TABLE eval_test_cases (
    id VARCHAR(255) PRIMARY KEY,
    dataset_id UUID REFERENCES eval_datasets(id),
    question TEXT NOT NULL,
    expected_answer TEXT,
    ground_truth_docs JSONB,  -- ["doc_id1", "doc_id2"]
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 实验运行
CREATE TABLE eval_experiments (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    dataset_id UUID REFERENCES eval_datasets(id),
    config JSONB NOT NULL,
    metrics_summary JSONB,
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT
);

-- 评估结果（可选：存到 JSON 文件或单独表）
CREATE TABLE eval_results (
    id UUID PRIMARY KEY,
    experiment_id UUID REFERENCES eval_experiments(id),
    test_case_id VARCHAR(255) REFERENCES eval_test_cases(id),
    retrieval_result JSONB,
    generation_result JSONB,
    metrics JSONB,
    passed BOOLEAN,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_experiments_dataset ON eval_experiments(dataset_id);
CREATE INDEX idx_experiments_created ON eval_experiments(started_at DESC);
CREATE INDEX idx_results_experiment ON eval_results(experiment_id);
```

### 9.2 Repository 实现

```python
class EvaluationRepository:
    """评估数据持久化"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def save_experiment(self, experiment: ExperimentRun) -> None:
        """保存实验及其结果"""
        
        # 保存实验记录
        stmt = insert(EvalExperiment).values(
            id=experiment.id,
            name=experiment.name,
            dataset_id=experiment.dataset_id,
            config=experiment.config.__dict__,
            metrics_summary=experiment.metrics_summary.__dict__,
            status=experiment.status,
            started_at=experiment.started_at,
            completed_at=experiment.completed_at,
            duration_seconds=experiment.duration_seconds,
        )
        await self.db.execute(stmt)
        
        # 批量保存结果
        if experiment.results:
            result_values = [
                {
                    "id": str(uuid.uuid4()),
                    "experiment_id": experiment.id,
                    "test_case_id": result.test_case_id,
                    "retrieval_result": result.retrieval.__dict__ if result.retrieval else None,
                    "generation_result": result.generation.__dict__ if result.generation else None,
                    "metrics": result.metrics,
                    "passed": result.passed,
                    "error": result.error,
                }
                for result in experiment.results
            ]
            await self.db.execute(insert(EvalResult).values(result_values))
        
        await self.db.commit()
    
    async def get_experiment(self, experiment_id: str) -> ExperimentRun:
        """加载实验及其结果"""
        # 实现略
        pass
    
    async def list_experiments(
        self,
        dataset_id: str | None = None,
        limit: int = 50,
    ) -> list[ExperimentRun]:
        """列出实验（按时间倒序）"""
        # 实现略
        pass
```

## 10. 实施路线图

### Phase 1: 核心评估引擎 (Week 1-2)

**目标**: 实现基础的评估能力

- [ ] 数据模型定义 (`evaluation/models.py`)
- [ ] 5 个核心指标实现:
  - Context Precision
  - Context Recall
  - Faithfulness (LLM-based)
  - Answer Relevancy (LLM-based)
  - Latency
- [ ] `RAGEvaluator` 核心引擎
- [ ] 数据库 Schema + Repository
- [ ] 单元测试

**产出**: 
```python
# 可通过代码运行评估
evaluator = RAGEvaluator(...)
result = await evaluator.run_experiment(dataset, config)
print(f"Overall Score: {result.metrics_summary.overall_score}")
```

### Phase 2: 测试用例管理 (Week 2-3)

**目标**: 支持测试集创建和管理

- [ ] JSON 格式测试集加载器
- [ ] 合成数据生成器（基于 LLM）
- [ ] 测试用例 CRUD API
- [ ] 数据集版本管理

**产出**:
```bash
# CLI 工具
ragmax eval create-dataset --name "cs_qa_v1"
ragmax eval add-case --dataset cs_qa_v1 --question "..." --answer "..."
ragmax eval generate-synthetic --source-ids doc1,doc2 --output dataset.json
```

### Phase 3: 实验对比与分析 (Week 3-4)

**目标**: 支持多实验对比

- [ ] `ExperimentComparison` 实现
- [ ] 指标差异计算
- [ ] 优化建议生成器（基于规则 + LLM）
- [ ] 导出报告（Markdown/HTML）

**产出**:
```bash
ragmax eval compare --baseline exp_001 --candidates exp_002,exp_003
# 输出对比报告和优化建议
```

### Phase 4: Web Dashboard (Week 4-6)

**目标**: 可视化界面

- [ ] React + FastAPI 前后端分离
- [ ] 4 个核心页面（概览、实验详情、对比、数据集管理）
- [ ] Recharts 图表集成
- [ ] 实时运行进度（WebSocket）

**产出**: 
访问 `http://localhost:3000/evaluation` 查看可视化 Dashboard

### Phase 5: 高级特性 (Week 6+)

**可选扩展**:

- [ ] A/B 测试模式（线上流量分流）
- [ ] 自动化回归测试（CI/CD 集成）
- [ ] 用户反馈收集（thumbs up/down）
- [ ] 在线学习（基于反馈调整参数）
- [ ] 更多指标（BLEU, ROUGE, BERTScore, 自定义指标）
- [ ] 对抗性测试用例生成
- [ ] 多维度切片分析（按难度、类别、语言等）

## 11. 技术栈建议

### 后端
- **框架**: FastAPI（已有）
- **评估 LLM**: 复用现有 `LLMClient`，支持 OpenAI / DeepSeek
- **数据库**: PostgreSQL（已有）
- **异步**: asyncio + asyncpg
- **依赖新增**:
  ```
  numpy>=1.24.0           # 分位数计算
  scipy>=1.10.0           # 统计分析
  nltk>=3.8               # ROUGE 计算（可选）
  bert-score>=0.3.13      # BERTScore（可选）
  ```

### 前端
- **框架**: React + TypeScript（已有）
- **图表**: Recharts / Apache ECharts
- **状态管理**: TanStack Query（已有）
- **UI**: 复用现有 UI 组件

### CLI
- **工具**: Click / Typer
- **位置**: `src/ragmax/cli/eval.py`

## 12. 配置示例

### 实验配置文件 (YAML)

```yaml
# experiments/baseline.yaml
name: "Baseline Configuration"

retrieval:
  embedding_model: "bge-large-zh-v1.5"
  top_k: 10
  enable_bm25: true
  enable_rerank: true
  rerank_model: "BAAI/bge-reranker-v2-m3"
  rerank_top_n: 5
  fusion_strategy: "rrf"

query_transform:
  strategy: "multi_query"  # original / hyde / multi_query
  multi_query_llm: "deepseek-chat"

generation:
  llm: "gpt-4o-mini"
  temperature: 0.0
  max_tokens: 1000

metrics:
  - name: "context_precision"
    threshold: 0.8
  - name: "context_recall"
    threshold: 0.9
  - name: "faithfulness"
    threshold: 0.95
  - name: "answer_relevancy"
    threshold: 0.85
```

## 13. 使用示例

### 完整评估流程

```python
from ragmax.evaluation import (
    RAGEvaluator,
    TestDataset,
    ExperimentConfig,
    load_dataset,
)

# 1. 加载测试集
dataset = load_dataset("tests/evaluation/datasets/customer_support.json")

# 2. 定义配置
config = ExperimentConfig(
    embedding_model="bge-large-zh-v1.5",
    top_k=10,
    enable_bm25=True,
    enable_rerank=True,
    rerank_model="BAAI/bge-reranker-v2-m3",
    rerank_top_n=5,
    fusion_strategy="rrf",
    query_strategy="multi_query",
    multi_query_llm="deepseek-chat",
    answer_llm="gpt-4o-mini",
    temperature=0.0,
    max_tokens=1000,
)

# 3. 运行评估
evaluator = RAGEvaluator(retrieval_service, metrics, llm_client)
experiment = await evaluator.run_experiment(
    dataset=dataset,
    config=config,
    name="baseline_2026_06_08",
)

# 4. 查看结果
print(f"Overall Score: {experiment.metrics_summary.overall_score:.2f}")
print(f"Faithfulness: {experiment.metrics_summary.faithfulness:.2f}")
print(f"Context Recall: {experiment.metrics_summary.context_recall:.2f}")
print(f"Pass Rate: {experiment.metrics_summary.pass_rate:.1%}")
print(f"P95 Latency: {experiment.metrics_summary.e2e_latency_p95:.0f}ms")

# 5. 对比实验
comparison = await compare_experiments(
    baseline_id=experiment.id,
    candidate_ids=["exp_002", "exp_003"],
)

for rec in comparison.recommendations:
    print(f"💡 {rec}")
```

## 14. 关键设计原则

1. **模块化**: 每个指标独立实现，易于扩展
2. **可配置**: 通过配置文件控制评估行为
3. **可追溯**: 所有实验记录持久化，可回溯
4. **自动化**: 支持 CI/CD 集成，PR 前自动评估
5. **可解释**: 提供详细的案例级别分析和优化建议
6. **成本意识**: 跟踪 token 消耗，平衡质量与成本

## 参考资料

- [DeepEval GitHub](https://github.com/confident-ai/deepeval)
- [RAG Evaluation Metrics (Confident AI)](https://www.confident-ai.com/blog/rag-evaluation-metrics-answer-relevancy-faithfulness-and-more)
- [RAG Evaluation Best Practices 2026](https://www.digitalapplied.com/blog/rag-system-metrics-recall-precision-faithfulness-2026)
- [Braintrust RAG Evaluation Guide](https://www.braintrust.dev/articles/rag-evaluation-metrics)

---

**下一步**: 开始 Phase 1 实现，先构建核心评估引擎 🚀
