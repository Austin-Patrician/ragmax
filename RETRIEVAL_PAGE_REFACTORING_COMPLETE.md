# RetrievalPage UI/UX 重构完成

## 概述

将 RetrievalPage 从简陋的界面重构为专业的 AI 对话界面，参考 DEEPSEEK 风格设计。

## 新增组件

### 1. ConversationSidebar（对话侧边栏）
**位置**: `web/src/components/retrieval/ConversationSidebar.tsx`

**功能**:
- 新建对话按钮
- 对话列表展示
- 搜索功能
- 对话切换和删除
- 可折叠设计

**设计特点**:
- 固定宽度 260px
- 对话项显示标题、预览、时间戳和数据集
- 鼠标悬停显示更多操作按钮
- 空状态提示

### 2. ChatMessageArea（聊天消息区域）
**位置**: `web/src/components/retrieval/ChatMessageArea.tsx`

**功能**:
- 用户消息和 AI 回复展示
- 引用来源展示
- 检索流程可视化（调试模式）
- 加载状态动画
- 空状态提示

**设计特点**:
- 头像区分用户和 AI
- 消息时间戳
- 来源卡片带评分
- 可折叠的检索步骤详情
- 三点加载动画

### 3. IntegratedInputBox（集成式输入框）
**位置**: `web/src/components/retrieval/IntegratedInputBox.tsx`

**功能**:
- 自动调整高度的文本输入框
- 发送按钮
- 底部工具栏（无分隔线设计）
- 数据集选择器
- 联网搜索开关
- 思考模式开关
- 调试模式开关
- 模型指示器

**设计特点**:
- 输入框和工具栏无缝集成
- 圆角卡片设计
- 工具按钮激活状态高亮
- 支持 Shift+Enter 换行
- Enter 发送消息

## 主页面重构

### RetrievalPage 新布局
**位置**: `web/src/pages/retrieval/RetrievalPage.tsx`

**布局结构**:
```
┌─────────────────────────────────────┐
│  Sidebar  │  Header                 │
│           ├─────────────────────────┤
│           │                         │
│  对话列表  │   Chat Message Area    │
│           │                         │
│           │   (滚动区域)             │
│           │                         │
│           ├─────────────────────────┤
│           │   Integrated Input Box  │
└─────────────────────────────────────┘
```

**功能**:
- 侧边栏可折叠
- 对话管理（创建、切换、删除）
- 消息发送和接收
- 模拟 API 调用（TODO: 接入真实后端）
- 调试模式切换
- 数据集集成

## 设计系统

基于 UI/UX Pro Max skill 生成的设计系统：

- **风格**: Flat Design
- **主色**: #6366F1 (Indigo)
- **副色**: #818CF8
- **CTA**: #10B981 (Emerald)
- **背景**: #F5F3FF
- **文本**: #1E1B4B
- **字体**: Fira Code / Fira Sans

## 技术栈

- React 18
- TypeScript (严格模式)
- CSS Modules
- React Query (数据获取)
- i18next (国际化)
- Lucide React (图标)

## 待实现功能 (TODO)

1. **后端 API 集成**:
   - [ ] 对话 CRUD API
   - [ ] 消息发送和接收 API
   - [ ] 实时流式响应
   - [ ] 对话持久化

2. **对话管理**:
   - [ ] 对话重命名
   - [ ] 对话搜索
   - [ ] 对话分组/标签
   - [ ] 导出对话

3. **消息功能**:
   - [ ] 消息编辑
   - [ ] 消息重新生成
   - [ ] 复制消息
   - [ ] Markdown 渲染
   - [ ] 代码高亮

4. **高级功能**:
   - [ ] 附件上传
   - [ ] 语音输入
   - [ ] 多模态支持
   - [ ] 上下文引用

## 文件清单

### 新增文件
- `web/src/components/retrieval/ConversationSidebar.tsx`
- `web/src/components/retrieval/ConversationSidebar.module.css`
- `web/src/components/retrieval/ChatMessageArea.tsx`
- `web/src/components/retrieval/ChatMessageArea.module.css`
- `web/src/components/retrieval/IntegratedInputBox.tsx`
- `web/src/components/retrieval/IntegratedInputBox.module.css`

### 修改文件
- `web/src/pages/retrieval/RetrievalPage.tsx` (完全重写)
- `web/src/pages/retrieval/RetrievalPage.module.css` (重新设计)
- `web/src/hooks/useIndexing.ts` (添加 useDatasets hook)
- `web/src/hooks/queryKeys.ts` (添加 datasets query keys)

### 国际化
已使用现有的 i18n keys：
- `retrieval.newConversation`
- `retrieval.conversations`
- `retrieval.noConversations`
- `retrieval.startConversation`
- `retrieval.typeMessage`
- `retrieval.sourcesReferenced`
- `retrieval.retrievalPipeline`
- `retrieval.toggleDebugMode`
- `retrieval.webSearch`
- `retrieval.thinkingMode`
- `retrieval.selectDataset`

## 构建状态

✅ TypeScript 编译成功
✅ Vite 构建成功
⚠️  Bundle 大小警告 (743 KB) - 建议后续优化

## 使用方法

1. 启动开发服务器:
```bash
cd web
npm run dev
```

2. 访问检索页面: http://localhost:5173/retrieval

3. 测试功能:
   - 点击"新建对话"创建对话
   - 在输入框输入消息并发送
   - 切换调试模式查看检索流程
   - 选择数据集进行检索

## 下一步

1. **后端 API 开发**: 实现对话和消息的 CRUD 接口
2. **实时通信**: 使用 WebSocket 或 SSE 实现流式响应
3. **性能优化**: 代码分割、懒加载、虚拟滚动
4. **增强体验**: Markdown 渲染、代码高亮、复制功能
5. **移动端适配**: 响应式设计优化

---

**重构完成时间**: 2026-06-09
**设计参考**: DEEPSEEK AI Chat Interface
**设计系统**: RAGMax - Flat Design
