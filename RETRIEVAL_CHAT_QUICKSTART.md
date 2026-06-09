# Retrieval Chat 页面 - 快速启动指南

## 🚀 启动方式

### 1. 启动开发服务器
```bash
cd web
npm run dev
```

### 2. 访问页面
打开浏览器访问：
```
http://localhost:5173/retrieval
```

---

## 🎮 功能演示

### 基础使用

1. **选择数据集**
   - 点击右下角 "Select dataset" 下拉框
   - 选择一个数据集（目前显示 mock 数据）

2. **发送消息**
   - 在输入框输入问题
   - 点击蓝色发送按钮（或按 Enter）

3. **查看回复**
   - AI 回复显示在聊天区域
   - 底部可以展开查看来源引用

### Dev 模式

1. **切换到 Dev 模式**
   - 点击底部工具栏的 "Prod" 按钮
   - 变为橙色的 "Dev" 按钮

2. **查看检索步骤**
   - 发送消息后，AI 回复顶部会显示黄色的检索流程框
   - 展开可以看到：
     - Query Understanding (45ms)
     - Vector Search (120ms)
     - Rerank (80ms)
     - Context Assembly (20ms)

### 其他功能

- **🌐 联网搜索**：点击地球图标（目前为 UI 演示）
- **🧠 思考模式**：点击大脑图标（目前为 UI 演示）
- **📟 模型选择**：点击模型下拉框选择不同模型
- **🏠 新建对话**：点击房子图标开始新对话

---

## 📊 当前状态

### ✅ 已完成
- [x] 完整的 UI 界面
- [x] Dev/Production 模式切换
- [x] 消息显示（用户 + AI）
- [x] 来源引用展示
- [x] 检索步骤展示（Dev 模式）
- [x] 底部工具栏
- [x] 国际化支持

### 🔄 Mock 数据
目前使用 mock 数据演示功能：
- 数据集列表：Documentation, Research Papers, Code Snippets
- AI 回复：固定的测试回复
- 来源引用：document1.pdf (p.5) [95%]
- 检索步骤：固定的 4 个步骤

### ⏳ 待集成
- [ ] 后端 API 集成
- [ ] 真实数据集加载
- [ ] 实际的 retrieval 调用
- [ ] 对话历史持久化
- [ ] 联网搜索实现
- [ ] 思考模式实现

---

## 🎯 测试场景

### 场景 1: Production 模式对话
1. 确保 "Prod" 按钮是灰色（未选中状态）
2. 选择数据集 "Documentation"
3. 输入问题："什么是 RAG？"
4. 发送消息
5. **预期**：看到用户消息 + AI 回复 + 来源引用（可折叠）

### 场景 2: Dev 模式对话
1. 点击 "Prod" 按钮切换到 "Dev" 模式（橙色）
2. 选择数据集 "Research Papers"
3. 输入问题："解释向量检索"
4. 发送消息
5. **预期**：
   - 顶部黄色框：Retrieval Pipeline（4个步骤）
   - 中间灰色框：AI 回复内容
   - 底部：Sources Referenced（可折叠）

### 场景 3: 功能开关
1. 点击 🌐 图标（联网搜索）
   - **预期**：图标变为青色高亮
2. 点击 🧠 图标（思考模式）
   - **预期**：图标变为橙色高亮
3. 再次点击可取消选中

### 场景 4: 模型切换
1. 点击模型下拉框 "gpt-4o-mini ▼"
2. 选择 "Claude 3.5 Sonnet"
3. **预期**：下拉框显示新选择的模型

---

## 🐛 已知限制

1. **无后端连接**
   - 当前所有数据都是 mock
   - 发送消息后 1 秒延迟模拟 API 调用

2. **对话历史**
   - 左侧对话列表为空（显示"暂无对话"）
   - 新建对话会清空当前消息

3. **功能开关无效**
   - 联网搜索、思考模式只是 UI 状态
   - 实际功能需要后端支持

4. **固定回复**
   - 所有问题都返回相同的 mock 回复
   - 检索步骤是固定的演示数据

---

## 🔧 开发提示

### 添加真实 API

在 `RetrievalPage.tsx` 的 `handleSend` 函数中：

```typescript
const handleSend = async () => {
  if (!input.trim() || !selectedDataset) return

  const userMessage: Message = { ... }
  setMessages((prev) => [...prev, userMessage])
  setInput('')

  try {
    // TODO: 替换为真实 API 调用
    const response = await fetch('/api/v1/retrieval/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: input,
        datasetId: selectedDataset,
        mode: mode,
        options: {
          webSearchEnabled,
          thinkingMode,
          model: selectedModel,
        },
      }),
    })

    const data = await response.json()
    
    const aiMessage: Message = {
      id: data.messageId,
      role: 'assistant',
      content: data.content,
      timestamp: data.timestamp,
      sources: data.sources,
      retrievalSteps: mode === 'dev' ? data.retrievalSteps : undefined,
    }

    setMessages((prev) => [...prev, aiMessage])
  } catch (error) {
    console.error('Failed to send message:', error)
    // TODO: 显示错误提示
  }
}
```

### 加载数据集列表

在 `BottomToolbar.tsx` 中：

```typescript
// 替换 mock 数据
const { data: datasets } = useDatasets()
const datasetOptions = datasets?.map(d => ({
  value: d.id,
  label: d.name,
})) || []
```

---

## 📝 后续任务

### 高优先级
1. **API 集成**
   - 创建 `/api/v1/retrieval/chat` 端点
   - 实现 POST 请求处理
   - 返回结构化响应

2. **数据集加载**
   - 使用现有的 `useDatasets` hook
   - 动态填充下拉框选项

3. **错误处理**
   - 添加 toast 通知
   - 网络错误提示
   - 重试机制

### 中优先级
4. **对话历史**
   - 保存对话到本地/服务器
   - 左侧列表展示历史对话
   - 点击切换对话

5. **加载状态**
   - 发送时禁用输入
   - 显示 loading 动画
   - Skeleton 占位符

### 低优先级
6. **打字效果**
   - AI 回复逐字显示
   - 更真实的交互体验

7. **性能优化**
   - 长对话虚拟化
   - 消息懒加载

---

## ✅ 验收标准

### UI 完整性
- [x] 左右两栏布局正常
- [x] 输入框固定在底部
- [x] 工具栏按钮可交互
- [x] 消息气泡样式正确

### 功能完整性
- [x] 可以输入并发送消息
- [x] Dev/Prod 模式切换生效
- [x] 检索步骤在 Dev 模式显示
- [x] 来源引用可折叠/展开
- [x] 工具栏所有按钮可点击

### 响应性
- [x] 自动滚动到最新消息
- [x] 悬停效果流畅
- [x] 按钮状态反馈及时

---

## 🎉 恭喜！

Retrieval Chat 页面已经完成基础实现，可以开始后端 API 集成了！

如有问题，请参考：
- 设计文档：`RETRIEVAL_CHAT_DESIGN_PLAN.md`
- 实现总结：`RETRIEVAL_CHAT_IMPLEMENTATION_SUMMARY.md`
- 源代码：`web/src/pages/retrieval/`
