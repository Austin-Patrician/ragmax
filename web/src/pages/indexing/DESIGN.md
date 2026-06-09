# IndexingPage 重构设计文档

## 设计目标

将 IndexingPage 从复杂的三栏控制面板重构为清晰的两段式布局，专注于**查看和检查**已完成的 Indexing 产物。

## 核心理念

- **自动化优先**：文件上传后自动触发 indexing，无需手动操作
- **检查为主**：页面用于检查和浏览 indexing 产物，而非执行操作
- **定制化展示**：每个阶段的产物使用专门设计的展示组件
- **简化交互**：移除创建 run、手动执行阶段等复杂操作

## 布局结构

```
┌─────────────────────┬──────────────────────────────────────────────┐
│                     │  StageTimeline (6 stages horizontal)         │
│  FileListPanel      ├──────────────────────────────────────────────┤
│                     │                                              │
│  ┌─────────────┐    │                                              │
│  │ file1.pdf   │    │  ArtifactViewer                              │
│  │ ✓ Completed │    │  (选中阶段的产物详情)                          │
│  └─────────────┘    │                                              │
│  ┌─────────────┐    │  - SourceConfigViewer                        │
│  │ file2.md    │    │  - BlocksTableViewer                         │
│  │ → Running   │    │  - ProfileAnalysisViewer                     │
│  └─────────────┘    │  - ChunksTableViewer                         │
│  ┌─────────────┐    │  - QualityEnrichViewer                       │
│  │ file3.txt   │    │  - VectorStatsViewer                         │
│  │ ✗ Failed    │    │                                              │
│  └─────────────┘    │                                              │
│                     │                                              │
└─────────────────────┴──────────────────────────────────────────────┘
```

## 组件层次

```
IndexingPage
├── FileListPanel
│   └── FileCard[] (显示文件名、状态、最新 run 信息)
└── IndexDetailPanel
    ├── StageTimeline (6 个 stage 卡片)
    └── ArtifactViewer
        ├── SourceConfigViewer
        ├── BlocksTableViewer
        ├── ProfileAnalysisViewer
        ├── ChunksTableViewer
        ├── QualityEnrichViewer
        └── VectorStatsViewer
```

## 交互流程

1. 用户在 Files 页面上传文件
2. 后端自动创建 pipeline run 并执行所有阶段
3. 用户切换到 Indexing 页面
4. 左侧显示所有已上传的文件及其 indexing 状态
5. 点击文件查看该文件最新的 pipeline run 详情
6. 右上显示 6 个阶段的执行状态
7. 点击阶段查看该阶段的产物
8. 产物使用定制化组件展示

## 产物展示策略

### Stage 1: source
**数据特征**: 配置信息、元数据
**展示组件**: `SourceConfigViewer`
**展示方式**: 
- 配置卡片（profile, parser, chunk_size, chunk_overlap）
- 源文件信息（filename, size, hash）
- 元数据 JSON 展示

### Stage 2: parse_blocks
**数据特征**: blocks 数组（block_id, block_type, page_no, text）
**展示组件**: `BlocksTableViewer`
**展示方式**:
- 分页表格，列：ID | Type | Page | Text (3 行截断)
- 支持按 block_type 筛选
- 支持分页（每页 50 条）

### Stage 3: analyze_profile
**数据特征**: profile 推荐结果、traits、策略配置
**展示组件**: `ProfileAnalysisViewer`
**展示方式**:
- Profile 卡片（推荐的 profile 名称）
- Traits 列表（识别的文档特征）
- 策略配置 JSON

### Stage 4: chunk_nodes
**数据特征**: chunks 数组（node_id, content_type, text, page_start, page_end）
**展示组件**: `ChunksTableViewer`
**展示方式**:
- 分页表格，列：ID | Type | Pages | Text (3 行截断)
- 显示 chunk 统计（总数、平均长度）

### Stage 5: quality_enrich
**数据特征**: 增强后的 nodes（带质量指标、warnings）
**展示组件**: `QualityEnrichViewer`
**展示方式**:
- 分页表格，列：ID | Quality Score | Warnings | Text
- 质量统计（平均分、警告数）
- 支持按质量分数排序

### Stage 6: vectorize
**数据特征**: embedding 结果、向量化统计
**展示组件**: `VectorStatsViewer`
**展示方式**:
- 统计卡片（总向量数、维度、成功/失败数）
- 向量化结果摘要
- 错误列表（如果有失败）

## 技术细节

### API 调用流程
1. `listSources()` - 获取所有文件
2. `listIndexPipelineRuns(sourceId)` - 获取文件的最新 run
3. `getIndexPipelineRun(runId)` - 获取 run 详情和 stages
4. `getIndexPipelineStageArtifacts(runId, stageName)` - 获取阶段产物列表
5. `getIndexArtifactData(artifactId)` - 获取产物数据

### 状态管理
```typescript
const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null)
const [selectedStage, setSelectedStage] = useState<IndexingStageName>('source')

// 基于 selectedSourceId 自动获取最新 run
const latestRun = useLatestPipelineRun(selectedSourceId)
const runDetail = useIndexPipelineRun(latestRun?.run_id)
const stageArtifacts = useIndexPipelineStageArtifacts(latestRun?.run_id, selectedStage)
```

### 响应式布局
- 桌面（>1024px）：左右分栏（30% / 70%）
- 平板（768-1024px）：左右分栏（35% / 65%）
- 手机（<768px）：上下堆叠

## 移除的功能

以下功能从新设计中移除（简化用户体验）：

- ✗ 文件上传表单（移至 Files 页面）
- ✗ 创建 Run 按钮
- ✗ 执行全部按钮
- ✗ 单个阶段执行/重新生成按钮
- ✗ Profile/Parser 选择器
- ✗ Chunk size/overlap 输入框
- ✗ Run 历史列表（只显示最新 run）
- ✗ 配置 JSON 编辑器

## 保留的功能

- ✓ 文件列表（带状态指示）
- ✓ 阶段时间线（带状态和耗时）
- ✓ 产物检查器（增强版）
- ✓ 产物数据展示（定制化组件）

## 实现计划

1. ✓ 创建设计文档
2. □ 更新国际化文本（中英文）
3. □ 实现 FileListPanel 组件
4. □ 实现 StageTimeline 组件
5. □ 实现各阶段的 Viewer 组件
6. □ 实现 ArtifactViewer 容器
7. □ 重写 IndexingPage 主组件
8. □ 更新 CSS 样式
9. □ 测试和调试
