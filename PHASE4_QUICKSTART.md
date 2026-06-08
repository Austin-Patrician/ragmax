# 🚀 Phase 4 Web Dashboard - 快速开始指南

## 立即体验评估平台 UI

---

## 📋 前置条件

1. Python 3.12+
2. Node.js 18+
3. PostgreSQL（用于数据持久化）
4. Qdrant（向量数据库）

---

## 🔧 启动步骤

### 1. 安装后端依赖
```bash
cd /Users/aa123456/code/python/ragmax

# 安装 Python 依赖
uv sync

# 运行数据库迁移
uv run alembic upgrade head
```

### 2. 启动后端服务
```bash
# 启动 FastAPI 服务
uv run uvicorn ragmax.main:app --reload --host 0.0.0.0 --port 8000

# 服务将运行在: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 3. 安装前端依赖
```bash
cd web

# 安装依赖（首次运行）
npm install

# 或使用 yarn
yarn install
```

### 4. 启动前端开发服务器
```bash
# 启动开发服务器
npm run dev

# 或使用 yarn
yarn dev

# 前端将运行在: http://localhost:5173
```

### 5. 访问评估页面
打开浏览器访问：
```
http://localhost:5173/evaluation
```

---

## 🎯 可用的 API 端点

### 数据集管理
```bash
# 列出所有数据集
curl http://localhost:8000/api/v1/evaluation/datasets

# 获取数据集详情
curl http://localhost:8000/api/v1/evaluation/datasets/{dataset_id}

# 创建数据集
curl -X POST http://localhost:8000/api/v1/evaluation/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Dataset",
    "description": "My first dataset",
    "version": "1.0.0",
    "test_cases": [
      {
        "question": "What is RAG?",
        "expected_answer": "Retrieval-Augmented Generation",
        "ground_truth_docs": ["doc_001"]
      }
    ]
  }'
```

### 实验管理
```bash
# 列出实验
curl http://localhost:8000/api/v1/evaluation/experiments

# 运行实验（TODO: 完整实现）
curl -X POST http://localhost:8000/api/v1/evaluation/experiments/run \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "dataset_001",
    "name": "Baseline Test",
    "config": {
      "top_k": 10,
      "enable_rerank": true
    }
  }'
```

---

## 🧪 测试数据准备

### 方式 1: 使用 CLI 创建测试数据
```bash
# 创建数据集
uv run ragmax-eval create-dataset \
  --name "Customer Support QA" \
  --description "客服场景测试" \
  --version "1.0.0"

# 添加测试用例
uv run ragmax-eval add-case \
  --dataset "Customer Support QA" \
  --question "如何重置密码？" \
  --answer "点击忘记密码链接" \
  --docs "doc_001"
```

### 方式 2: 使用 Python 代码
```python
import asyncio
from datetime import datetime
from uuid import uuid4

from ragmax.evaluation.models import EvalTestCase, TestDataset
from ragmax.evaluation.repository import EvaluationRepository
from ragmax.infrastructure.db.session import AsyncSessionLocal

async def create_test_data():
    # 创建测试数据集
    dataset = TestDataset(
        id=str(uuid4()),
        name="Demo Dataset",
        description="演示数据集",
        test_cases=[
            EvalTestCase(
                id="tc_001",
                question="什么是 RAG？",
                expected_answer="RAG 是检索增强生成技术",
                ground_truth_docs=["doc_001"],
                metadata={"difficulty": "easy"},
                created_at=datetime.now(),
            ),
            EvalTestCase(
                id="tc_002",
                question="RAG 有什么优势？",
                expected_answer="RAG 可以利用外部知识库...",
                ground_truth_docs=["doc_002", "doc_003"],
                metadata={"difficulty": "medium"},
                created_at=datetime.now(),
            ),
        ],
        version="1.0.0",
        created_at=datetime.now(),
    )

    # 保存到数据库
    async with AsyncSessionLocal() as session:
        repo = EvaluationRepository(session)
        await repo.create_dataset(dataset)
        print(f"✅ Dataset created: {dataset.id}")

# 运行
asyncio.run(create_test_data())
```

### 方式 3: 使用 API 直接创建
```bash
curl -X POST http://localhost:8000/api/v1/evaluation/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Quick Test Dataset",
    "description": "通过 API 创建的测试数据集",
    "version": "1.0.0",
    "test_cases": [
      {
        "question": "测试问题 1",
        "expected_answer": "测试答案 1",
        "ground_truth_docs": ["doc_001"],
        "metadata": {"difficulty": "easy"}
      },
      {
        "question": "测试问题 2",
        "expected_answer": "测试答案 2",
        "ground_truth_docs": ["doc_002"],
        "metadata": {"difficulty": "medium"}
      }
    ]
  }'
```

---

## 📸 预期效果

### 评估概览页面应该显示：

1. **关键指标卡片**
   - 数据集总数
   - 实验总数
   - 测试用例总数
   - 平均通过率

2. **最近数据集**
   - 数据集名称和版本
   - 测试用例数量
   - 创建时间

3. **最近实验**
   - 实验名称和状态
   - 核心指标（得分、通过率、延迟）
   - 执行时间

---

## 🔍 调试技巧

### 检查后端 API
```bash
# 测试 API 是否正常
curl http://localhost:8000/api/v1/health

# 查看 API 文档
open http://localhost:8000/docs
```

### 检查前端开发服务器
```bash
# 前端日志会显示编译错误
npm run dev

# 检查浏览器控制台
# F12 -> Console -> 查看 API 请求和错误
```

### 检查数据库
```bash
# 连接 PostgreSQL
psql -U your_user -d ragmax

# 查看数据集表
SELECT * FROM eval_datasets;

# 查看测试用例表
SELECT * FROM eval_test_cases;
```

---

## 🐛 常见问题

### 1. 前端无法连接后端
**症状**: API 请求失败，CORS 错误

**解决**:
- 检查后端是否运行在 `http://localhost:8000`
- 检查前端 API client 的 baseURL 配置
- 确保后端已配置 CORS

### 2. 数据库连接失败
**症状**: 启动时报错 "Could not connect to database"

**解决**:
```bash
# 检查 PostgreSQL 是否运行
pg_isready

# 检查 .env 配置
cat .env | grep DATABASE_URL

# 运行迁移
uv run alembic upgrade head
```

### 3. 页面显示"No datasets yet"
**症状**: 页面正常但没有数据

**解决**:
- 使用上面的方法创建测试数据
- 检查 API 响应是否正常
- 查看浏览器控制台的网络请求

---

## 📚 相关文档

- **完整设计文档**: `EVALUATION_PLATFORM_DESIGN.md`
- **Phase 1 总结**: `PHASE1_EVALUATION_SUMMARY.md`
- **Phase 2 总结**: `PHASE2_EVALUATION_SUMMARY.md`
- **Phase 4 总结**: `PHASE4_PART1_COMPLETE.md`

---

## 🎉 成功标志

当你看到以下内容时，说明一切正常：

✅ 后端 API 运行在 http://localhost:8000  
✅ API 文档可访问 http://localhost:8000/docs  
✅ 前端运行在 http://localhost:5173  
✅ 评估页面显示 http://localhost:5173/evaluation  
✅ 导航栏显示 "Evaluation" 选项  
✅ 页面显示数据集和实验列表（或空状态提示）  

---

## 🚀 下一步

1. 浏览评估概览页面
2. 创建第一个测试数据集
3. 查看数据集详情（即将实现）
4. 运行第一个评估实验（即将实现）
5. 查看实验结果和对比（即将实现）

享受使用 RAG 评估平台！🎊
