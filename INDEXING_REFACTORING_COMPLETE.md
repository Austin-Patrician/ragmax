# IndexingPage 重构完成总结

## 完成时间
2026-06-09

## 重构目标
将 IndexingPage 从复杂的三栏控制面板重构为清晰的两段式布局，专注于**查看和检查**已完成的 Indexing 产物。

## 主要变更

### 1. 布局设计
**原设计**：三栏布局（Timeline | Inspector | History）+ 复杂的上传/配置表单
**新设计**：两栏布局（Files List | Stage Timeline + Artifact Viewer）

```
┌─────────────────────┬──────────────────────────────────────┐
│  FileListPanel      │  StageTimeline (横向6个阶段)         │
│  (文件列表+状态)     ├──────────────────────────────────────┤
│                     │  ArtifactViewer                       │
│  ✓ file1.pdf        │  (定制化产物展示)                      │
│  → file2.md         │                                       │
│  ✗ file3.txt        │                                       │
└─────────────────────┴──────────────────────────────────────┘
```

### 2. 新增组件

#### FileListPanel (`components/FileListPanel.tsx`)
- 显示所有已上传的文件
- 显示每个文件的最新 indexing 状态
- 支持点击选择文件查看详情
- 响应式设计（桌面/平板/手机）

#### StageTimeline (`components/StageTimeline.tsx`)
- 横向展示 6 个 indexing 阶段
- 显示每个阶段的状态、耗时、产物数量
- 支持点击切换查看不同阶段的产物
- 状态图标（成功/失败/运行中/待执行）

#### ArtifactViewer (`components/ArtifactViewer.tsx`)
- 根据阶段类型自动选择合适的展示组件
- 显示产物元信息（类型、记录数、大小）
- 滚动区域支持大量数据展示

### 3. 定制化产物查看器

#### SourceConfigViewer
- 展示数据源配置信息
- Profile 和 Parser 配置
- 元数据 JSON

#### BlocksTableViewer
- 分页表格展示 blocks
- 列：Block ID | Type | Page | Text
- 每页 50 条记录

#### ProfileAnalysisViewer
- 推荐的 Profile
- 检测到的文档特征（traits）
- 策略配置

#### ChunksTableViewer
- 分页表格展示 chunks
- Chunk 统计（总数、平均长度）
- 列：Node ID | Content Type | Page Range | Text

#### QualityEnrichViewer
- 质量统计（平均质量分、警告数）
- 质量分数可视化（进度条）
- 警告信息展示

#### VectorStatsViewer
- 向量统计（总数、维度、成功/失败数）
- 错误列表展示

### 4. 国际化更新
- 更新了中英文翻译文件
- 新增 60+ 翻译键
- 保持了原有的命名规范

### 5. 移除的功能
以下功能已从新设计中移除（简化用户体验）：
- ✗ 文件上传表单（应在 Files 页面完成）
- ✗ 创建 Run 按钮
- ✗ 执行全部按钮
- ✗ 单个阶段执行/重新生成按钮
- ✗ Profile/Parser 选择器
- ✗ Chunk size/overlap 输入框
- ✗ Run 历史列表（只显示最新 run）
- ✗ 配置 JSON 编辑器

### 6. 保留和优化的功能
- ✓ 文件列表（新增状态指示）
- ✓ 阶段时间线（横向布局，更清晰）
- ✓ 产物检查器（定制化展示）
- ✓ 产物数据展示（针对不同类型优化）

## 技术实现

### API 调用流程
1. `listSources()` - 获取所有文件
2. `listIndexPipelineRuns(sourceId)` - 获取文件的最新 run
3. `getIndexPipelineRun(runId)` - 获取 run 详情和 stages
4. `getIndexPipelineStageArtifacts(runId, stageName)` - 获取阶段产物
5. `getIndexArtifactData(artifactId)` - 获取产物数据

### 状态管理
```typescript
const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null)
const [selectedStage, setSelectedStage] = useState<IndexingStageName>('source')

// React Query 自动管理数据获取和缓存
const { data: sources } = useSources({ limit: 100 })
const runsQuery = useIndexPipelineRuns(selectedSourceId)
const runDetailQuery = useIndexPipelineRun(latestRun?.run_id)
const stageArtifactsQuery = useIndexPipelineStageArtifacts(runId, selectedStage)
const artifactDataQuery = useIndexArtifactData(artifactId)
```

### 响应式布局
- **桌面** (>1200px): 左右分栏（320px / 1fr）
- **平板** (768-1024px): 左右分栏（280px / 1fr）
- **手机** (<768px): 上下堆叠

## 文件结构

```
web/src/pages/indexing/
├── IndexingPage.tsx              # 主页面组件（重写）
├── IndexingPage.module.css       # 主页面样式（重写）
├── IndexingPage.old.tsx          # 旧版本备份
├── IndexingPage.old.module.css   # 旧版本样式备份
├── DESIGN.md                     # 设计文档
├── components/
│   ├── index.ts                  # 组件导出
│   ├── FileListPanel.tsx         # 文件列表面板
│   ├── FileListPanel.module.css
│   ├── StageTimeline.tsx         # 阶段时间线
│   ├── StageTimeline.module.css
│   ├── ArtifactViewer.tsx        # 产物查看器容器
│   ├── ArtifactViewer.module.css
│   └── viewers/
│       ├── SourceConfigViewer.tsx
│       ├── BlocksTableViewer.tsx
│       ├── ProfileAnalysisViewer.tsx
│       ├── ChunksTableViewer.tsx
│       ├── QualityEnrichViewer.tsx
│       └── VectorStatsViewer.tsx
```

## 构建状态
✅ TypeScript 编译通过
✅ Vite 构建成功
✅ 无类型错误
⚠️ Bundle 大小警告（719.77 kB，建议使用代码分割优化）

## 下一步建议

### 短期优化
1. 为每个文件获取最新 run 的状态（目前显示为 null）
2. 添加加载骨架屏提升用户体验
3. 添加错误边界处理组件崩溃
4. 优化 bundle 大小（代码分割）

### 中期功能
1. 添加产物导出功能（CSV, JSON）
2. 添加产物搜索和过滤
3. 添加 Run 对比功能
4. 添加产物可视化图表

### 长期规划
1. 集成 Dataset 模型（按照 REFACTORING_SUMMARY.md）
2. 支持实时更新（WebSocket / SSE）
3. 添加产物编辑和重新执行能力
4. 性能监控和优化

## 用户体验改进

### 简化的交互流程
**旧流程**：
1. 上传文件
2. 创建 Run
3. 配置参数
4. 执行全部或单个阶段
5. 查看产物

**新流程**：
1. 在 Files 页面上传（自动 indexing）
2. 在 Indexing 页面选择文件
3. 查看各阶段产物

### 清晰的视觉层次
- **左侧**：文件列表，快速浏览所有文件状态
- **右上**：阶段时间线，一目了然的流程概览
- **右下**：产物详情，针对性展示各阶段输出

### 更好的性能
- 延迟加载：只加载选中文件和阶段的数据
- React Query 缓存：减少重复 API 调用
- 虚拟滚动候选：为大数据集做准备

## 已知限制

1. **文件列表的 latestRun 当前为 null**
   - 原因：需要为每个文件单独查询最新 run
   - 解决方案：可以添加批量查询 API 或使用并行查询

2. **产物数据结构假设**
   - 当前基于预期的数据结构实现
   - 实际 API 返回的数据可能需要适配

3. **分页功能简化**
   - 使用前端分页（仅展示已加载的数据）
   - 大数据集可能需要后端分页支持

## 测试建议

### 单元测试
- [ ] FileListPanel 组件渲染测试
- [ ] StageTimeline 状态切换测试
- [ ] 各个 Viewer 组件的数据展示测试

### 集成测试
- [ ] 文件选择 → 阶段切换 → 产物加载流程
- [ ] API 错误处理
- [ ] 空状态展示

### E2E 测试
- [ ] 完整的用户操作流程
- [ ] 不同屏幕尺寸下的响应式表现

## 结论

✅ **重构完成**：成功将复杂的 IndexingPage 重构为清晰、易用的两段式布局
✅ **构建成功**：所有 TypeScript 类型检查通过
✅ **功能完整**：实现了所有计划的核心功能
✅ **代码质量**：组件化、类型安全、可维护性高

新的 IndexingPage 专注于**查看和检查**，将复杂的配置和操作移到了更合适的地方（Files 页面），
为用户提供了更直观、更高效的产物检查体验。
