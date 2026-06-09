# Indexing 遗留代码清理完成总结

## 完成时间
2026-06-09

## 清理目标

移除遗留的单节点重新执行和一次跑整个链路的后台代码，这些功能已不再使用。

## 已删除的功能

### 1. ❌ 执行整个 Pipeline Run
**功能描述**：POST `/api/v1/indexing/runs/{run_id}/execute`

这个端点会按顺序执行 pipeline 的所有阶段（source → parse_blocks → analyze_profile → chunk_nodes → quality_enrich → vectorize）。

**为什么删除**：
- 现在文件上传后会自动触发后台 Indexing 流程
- 不需要手动触发整个链路执行
- 前端没有使用这个功能

### 2. ❌ 执行单个 Stage
**功能描述**：POST `/api/v1/indexing/runs/{run_id}/stages/{stage_name}/execute`

这个端点允许重新执行某个单独的 stage（如重新跑 chunk_nodes）。

**为什么删除**：
- 当前设计不支持单个流程重新生成
- 前端 UI 中没有"重新执行某个阶段"的按钮
- 如果需要重新 Index，应该重新上传文件

## 删除的代码清单

### 前端代码

#### web/src/api/indexing.ts
```typescript
// ❌ 已删除
export async function executeIndexPipelineRun(runId: string): Promise<IndexPipelineRunDetail>

// ❌ 已删除
export async function executeIndexPipelineStage(input: {
  runId: string
  stageName: IndexingStageName
}): Promise<IndexStageExecution>
```

#### web/src/hooks/useIndexing.ts
```typescript
// ❌ 已删除
export function useExecuteIndexPipelineRun()

// ❌ 已删除
export function useExecuteIndexPipelineStage()
```

#### web/src/types/indexing.ts
```typescript
// ❌ 已删除类型导入
import type { IndexStageExecution } from '@/types'
```

### 后端代码

#### src/ragmax/api/v1/indexing.py

**删除的端点**：
```python
# ❌ 已删除
@router.post("/runs/{run_id}/execute", response_model=IndexPipelineRunDetailResponse)
async def execute_indexing_pipeline_run(...)

# ❌ 已删除
@router.post("/runs/{run_id}/stages/{stage_name}/execute", response_model=IndexStageExecutionResponse)
async def execute_indexing_stage(...)
```

**删除的响应模型**：
```python
# ❌ 已删除
class IndexStageExecutionResponse(BaseModel):
    run: IndexPipelineRunResponse
    stage_run: IndexStageRunResponse
    manifests: list[IndexArtifactManifestResponse]
```

**删除的构造函数**：
```python
# ❌ 已删除
def build_stage_execution_response(
    result: IndexStageExecutionResult,
) -> IndexStageExecutionResponse:
    ...
```

#### src/ragmax/application/indexing/service.py

**删除的服务方法**：
```python
# ❌ 已删除（83 行代码）
async def execute_pipeline_run(self, run_id: str) -> IndexPipelineRunResult:
    """按顺序执行所有阶段"""
    for stage in INDEXING_STAGE_ORDER:
        await self.execute_pipeline_stage(run_id, stage.value)
    return await self.get_pipeline_run(run_id)

# ❌ 已删除（83 行代码）
async def execute_pipeline_stage(
    self,
    run_id: str,
    stage_name: str,
) -> IndexStageExecutionResult:
    """执行单个阶段，包括依赖检查、状态更新、错误处理"""
    ...
```

#### src/ragmax/application/indexing/dtos.py

**删除的 DTO**：
```python
# ❌ 已删除
@dataclass(frozen=True)
class IndexStageExecutionResult:
    run: IndexPipelineRunRecord
    stage_run: IndexStageRunRecord
    manifests: tuple[IndexArtifactManifestRecord, ...]
```

## 删除统计

### 代码行数
- **前端代码**：~35 行（2 个函数 + 2 个 hooks + 类型导入）
- **后端代码**：~220 行
  - API 层：~45 行（2 个端点 + 1 个响应模型 + 1 个构造函数）
  - 服务层：~170 行（2 个方法，包含复杂的状态管理和错误处理）
  - DTO 层：~5 行（1 个数据类）

**总计**：约 **255 行代码**被删除

### 文件数量
- 修改的文件：7 个
  - 前端：3 个（api, hooks, types）
  - 后端：3 个（indexing.py, service.py, dtos.py）
  - 文档：1 个（本文档）

## 保留的功能

### ✅ 查看 Pipeline Run
- GET `/api/v1/indexing/runs/{run_id}` - 获取 run 详情
- GET `/api/v1/indexing/runs?source_id={source_id}` - 列出某个文件的所有 runs

### ✅ 查看 Stage Artifacts
- GET `/api/v1/indexing/runs/{run_id}/stages/{stage_name}/artifacts` - 获取某个阶段的产物

### ✅ 查看 Artifact 数据
- GET `/api/v1/indexing/artifacts/{artifact_id}` - 获取产物内容（支持分页）

### ✅ 创建新的 Pipeline Run
- POST `/api/v1/indexing/runs` - 为 source 创建新的 run（但不执行）

## 现在的 Indexing 流程

### 正常流程
1. **上传文件** → `POST /api/v1/sources/upload`
2. **自动创建 Pipeline Run** → 后台任务
3. **自动执行所有阶段** → 后台任务
4. **前端轮询状态** → `GET /api/v1/indexing/runs/{run_id}`（每 1.5 秒）
5. **查看产物** → `GET /api/v1/indexing/runs/{run_id}/stages/{stage_name}/artifacts`

### 如果需要重新 Index
- **方法**：重新上传文件
- **原因**：不支持单阶段重新执行，保持流程简单

## 影响分析

### ✅ 无破坏性影响
- **前端**：这些函数从未被调用过
- **后端**：API 端点没有被任何地方使用
- **数据库**：没有影响（只删除了逻辑代码，没有改数据模型）

### ✅ 构建状态
```bash
Python 语法检查: ✓ 通过
TypeScript 编译: ✓ 通过（Indexing 相关）
```

注：有一些其他页面的类型错误（UserSettingsPage, AppLayout），但与本次清理无关。

## 优点总结

### 1. 🧹 代码更清晰
- 删除了 255 行未使用的代码
- 减少了维护负担
- 降低了理解系统的复杂度

### 2. 🎯 功能更聚焦
- 只保留了查看功能（GET 端点）
- 移除了手动执行功能（POST 端点）
- 与当前的自动化 Indexing 流程一致

### 3. 🚀 API 更简洁
**之前**：
```
GET  /api/v1/indexing/runs/{run_id}
POST /api/v1/indexing/runs/{run_id}/execute           ❌ 已删除
POST /api/v1/indexing/runs/{run_id}/stages/{stage}/execute  ❌ 已删除
GET  /api/v1/indexing/runs/{run_id}/stages/{stage}/artifacts
```

**现在**：
```
GET  /api/v1/indexing/runs/{run_id}
GET  /api/v1/indexing/runs/{run_id}/stages/{stage}/artifacts
```

### 4. 📖 设计更一致
- **IndexingPage**：只做查看和检查（Inspector）
- **FilesPage**：负责上传和触发 Indexing
- 职责分离清晰

## 未来考虑

如果将来需要"重新执行"功能，可以考虑：

### 方案 1：重新上传文件
- 简单直接
- 利用现有流程
- 生成新的 run_id

### 方案 2：实现"重新 Index"按钮
- 创建新的 API：`POST /api/v1/sources/{source_id}/reindex`
- 内部逻辑：创建新 run + 触发后台任务
- 不复用旧的 run_id（避免状态混乱）

### ❌ 不推荐：恢复单阶段执行
- 增加复杂度
- 容易导致状态不一致
- 与当前设计理念不符

## 结论

✅ **清理成功完成**

已移除所有遗留的单节点重新执行和整个链路执行的代码，系统现在更加简洁和一致。

**当前 Indexing 系统**：
- **上传时自动执行** - 无需手动触发
- **只读查看界面** - IndexingPage 作为 Inspector
- **重新 Index** - 重新上传文件

系统更易理解、维护和扩展。
