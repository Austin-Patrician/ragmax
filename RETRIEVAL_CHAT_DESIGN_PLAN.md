# Retrieval Chat 页面设计方案（修订版）

## 📋 需求分析

### 核心功能
1. **Dev/Production 模式切换** - 放在输入框底部
2. **对话界面** - 聊天框（参考图片布局）
3. **基于 dataset 进行 retrieval**
4. **结构化展示 source 来源**
5. **支持联网搜索**
6. **支持思考模式**
7. **模型选择器** - 放在输入框底部

---

## 🎨 设计系统（浅色主题）

### 配色方案（基于 ui-ux-pro-max 推荐）
```css
/* 浅色主题 */
--color-primary: #1E40AF;          /* 蓝色 - 主色调 */
--color-secondary: #3B82F6;        /* 亮蓝色 - 次要 */
--color-cta: #22C55E;              /* 绿色 - 行动按钮 */
--color-background: #F8FAFC;       /* 浅灰蓝 - 页面背景 */
--color-surface: #FFFFFF;          /* 白色 - 卡片背景 */
--color-text: #1E3A8A;             /* 深蓝 - 主文本 */
--color-text-secondary: #64748B;   /* 中灰 - 次要文本 */

/* 语义化颜色 */
--color-user-message: #3B82F6;     /* 蓝色 - 用户消息 */
--color-ai-message: #F1F5F9;       /* 浅灰 - AI 回复背景 */
--color-thinking: #F59E0B;         /* 琥珀色 - 思考过程 */
--color-source: #10B981;           /* 翠绿色 - 来源引用 */
--color-web-search: #06B6D4;       /* 青色 - 联网搜索 */
--color-border: #E2E8F0;           /* 边框 */
```

### 字体系统
```css
--font-heading: 'Fira Code', monospace;      /* 标题 - 技术感 */
--font-body: 'Fira Sans', sans-serif;        /* 正文 - 数据友好 */
--font-code: 'Fira Code', monospace;         /* 代码块 */
```

---

## 📐 布局设计（简化版 - 两栏）

### 整体布局

```
┌─────────────────────────────────────────────────────────────────┐
│  Logo              [Dataset] [Chat] [Search] [Agent] ...        │ ← Top Nav
├───────────┬─────────────────────────────────────────────────────┤
│           │                                                      │
│ 📂        │              Chat Messages Area                      │
│           │                                                      │
│ Conversa- │   ┌────────────────────────────────────────────┐   │
│ tions     │   │ User: 什么是 RAG？                          │   │
│ List      │   └────────────────────────────────────────────┘   │
│           │                                                      │
│ [+ New]   │   ┌────────────────────────────────────────────┐   │
│           │   │ AI: RAG (Retrieval Augmented Generation)   │   │
│ • Conv 1  │   │ 是一种结合检索和生成的技术...                │   │
│ • Conv 2  │   │                                            │   │
│ • Conv 3  │   │ 📚 Sources:                                │   │
│           │   │ • document1.pdf (p.5) [95%]                │   │
│           │   │ • guide.md [88%]                           │   │
│           │   └────────────────────────────────────────────┘   │
│           │                                                      │
│           │   [Dev Mode: 展开检索步骤 👇]                       │
│ [Search]  │   ┌────────────────────────────────────────────┐   │
│           │   │ 🔍 Retrieval Pipeline                       │   │
│           │   │ ├─ 1️⃣ Query Understanding (45ms)           │   │
│           │   │ ├─ 2️⃣ Vector Search: 5 results (120ms)     │   │
│           │   │ ├─ 3️⃣ Rerank: top 3 (80ms)                 │   │
│           │   │ └─ 4️⃣ Context Assembly (20ms)              │   │
│           │   └────────────────────────────────────────────┘   │
│           │                                                      │
│ (280px)   │                                                      │
├───────────┴─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [📎] [Type your message...]                      [🎤] [▶] │  │ ← Input
│  └──────────────────────────────────────────────────────────┘  │
│  [🏠] [🔧Dev] [gpt-4o-mini ▼] [🌐] [🧠] [Dataset: docs ▼]     │  ← Toolbar
└─────────────────────────────────────────────────────────────────┘
```

**关键变化**：
1. ✅ 去掉右侧栏，改为底部工具栏
2. ✅ 所有设置放在输入框下方一行
3. ✅ 浅色主题为主

---

## 🧩 核心组件设计

### 1. Bottom Toolbar（底部工具栏） - 核心设计

**位置**：输入框正下方

```tsx
<Group className={styles.bottomToolbar} gap="xs" justify="space-between">
  {/* 左侧：主要功能 */}
  <Group gap="xs">
    {/* 首页按钮 */}
    <Tooltip label="New conversation">
      <ActionIcon
        variant="subtle"
        size="md"
        onClick={handleNewConversation}
      >
        <IconHome size={18} />
      </ActionIcon>
    </Tooltip>
    
    {/* Dev/Production 模式切换 */}
    <Tooltip label="Toggle debug mode">
      <Button
        variant={mode === 'dev' ? 'filled' : 'subtle'}
        color={mode === 'dev' ? 'orange' : 'gray'}
        size="xs"
        leftSection={<IconBug size={16} />}
        onClick={() => setMode(mode === 'dev' ? 'production' : 'dev')}
      >
        {mode === 'dev' ? 'Dev' : 'Prod'}
      </Button>
    </Tooltip>
    
    {/* 模型选择器 */}
    <Select
      value={selectedModel}
      onChange={setSelectedModel}
      data={[
        { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
        { value: 'gpt-4o', label: 'GPT-4o' },
        { value: 'claude-3.5-sonnet', label: 'Claude 3.5 Sonnet' },
        { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
      ]}
      size="xs"
      w={160}
      leftSection={<IconCpu size={16} />}
      rightSection={<IconChevronDown size={14} />}
      comboboxProps={{ shadow: 'md' }}
    />
  </Group>
  
  {/* 中间：功能开关 */}
  <Group gap="xs">
    {/* 联网搜索 */}
    <Tooltip label="Web search">
      <ActionIcon
        variant={webSearchEnabled ? 'filled' : 'subtle'}
        color={webSearchEnabled ? 'cyan' : 'gray'}
        size="md"
        onClick={() => setWebSearchEnabled(!webSearchEnabled)}
      >
        <IconWorld size={18} />
      </ActionIcon>
    </Tooltip>
    
    {/* 思考模式 */}
    <Tooltip label="Thinking mode">
      <ActionIcon
        variant={thinkingMode ? 'filled' : 'subtle'}
        color={thinkingMode ? 'orange' : 'gray'}
        size="md"
        onClick={() => setThinkingMode(!thinkingMode)}
      >
        <IconBrain size={18} />
      </ActionIcon>
    </Tooltip>
  </Group>
  
  {/* 右侧：Dataset 选择 */}
  <Group gap="xs">
    <Select
      value={selectedDataset}
      onChange={setSelectedDataset}
      data={datasets}
      size="xs"
      w={180}
      placeholder="Select dataset..."
      leftSection={<IconDatabase size={16} />}
      rightSection={<IconChevronDown size={14} />}
      comboboxProps={{ shadow: 'md' }}
    />
  </Group>
</Group>
```

**样式**：
```css
.bottomToolbar {
  padding: 8px 16px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  border-radius: 0 0 12px 12px;
}
```

---

### 2. Input Area（输入区域）

**完整结构**：
```tsx
<Paper className={styles.inputContainer} withBorder shadow="sm">
  {/* 输入框 */}
  <Group className={styles.inputBar} gap="sm" align="flex-end">
    <ActionIcon size="lg" variant="subtle" color="gray">
      <IconPaperclip size={20} />
    </ActionIcon>
    
    <Textarea
      placeholder="Type your message..."
      autosize
      minRows={1}
      maxRows={6}
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyDown={handleKeyDown}
      className={styles.textarea}
      styles={{
        input: {
          border: 'none',
          background: 'transparent',
          fontSize: 14,
        }
      }}
    />
    
    <Group gap="xs">
      <ActionIcon size="lg" variant="subtle" color="gray">
        <IconMicrophone size={20} />
      </ActionIcon>
      
      <ActionIcon
        size="lg"
        variant="filled"
        color="blue"
        onClick={handleSend}
        disabled={!input.trim()}
      >
        <IconSend size={20} />
      </ActionIcon>
    </Group>
  </Group>
  
  {/* 底部工具栏 */}
  <BottomToolbar {...toolbarProps} />
</Paper>
```

**样式**：
```css
.inputContainer {
  position: fixed;
  bottom: 16px;
  left: 296px; /* 280px sidebar + 16px gap */
  right: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  z-index: 100;
}

.inputBar {
  padding: 12px 16px;
}

.textarea {
  flex: 1;
  min-height: 42px;
}
```

---

### 3. Message Bubble（消息气泡 - 浅色版）

#### User Message
```tsx
<div className={styles.userMessageWrapper}>
  <div className={styles.userMessage}>
    <Text>{message.content}</Text>
    <Text size="xs" c="dimmed" mt={4}>{timestamp}</Text>
  </div>
  <Avatar color="blue" radius="xl" size="sm">
    {user.name[0]}
  </Avatar>
</div>
```

**样式**：
```css
.userMessageWrapper {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 16px;
}

.userMessage {
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
  color: white;
  border-radius: 18px 18px 4px 18px;
  padding: 12px 16px;
  max-width: 65%;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
}
```

#### AI Message
```tsx
<div className={styles.aiMessageWrapper}>
  <Avatar color="violet" radius="xl" size="sm">
    <IconSparkles size={18} />
  </Avatar>
  
  <Stack className={styles.aiMessageStack} gap="md">
    {/* Dev Mode: Retrieval Steps - 顶部显示 */}
    {mode === 'dev' && message.retrievalSteps && (
      <Paper withBorder p="md" radius="md" className={styles.retrievalSteps}>
        <RetrievalSteps steps={message.retrievalSteps} />
      </Paper>
    )}
    
    {/* Thinking indicator */}
    {isThinking && (
      <Alert
        icon={<IconBrain size={18} />}
        color="orange"
        variant="light"
      >
        <Group gap="xs">
          <Loader size="xs" />
          <Text size="sm">Thinking...</Text>
        </Group>
      </Alert>
    )}
    
    {/* AI Response - 中间主体内容 */}
    <Paper className={styles.aiMessage} radius="md">
      <Markdown>{message.content}</Markdown>
      <Text size="xs" c="dimmed" mt="sm">{timestamp}</Text>
    </Paper>
    
    {/* Sources - 底部折叠区域 */}
    {message.sources && message.sources.length > 0 && (
      <SourceReferences sources={message.sources} />
    )}
  </Stack>
</div>
```

**样式**：
```css
.aiMessageWrapper {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.aiMessage {
  background: #F1F5F9;
  border-radius: 18px 18px 18px 4px;
  padding: 16px;
  max-width: 75%;
  border-left: 3px solid #8B5CF6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
```

---

### 4. Source References（来源引用 - 简化版）

```tsx
<Accordion variant="contained" mt="md">
  <Accordion.Item value="sources">
    <Accordion.Control>
      <Group gap="xs">
        <ThemeIcon size="sm" color="green" variant="light">
          <IconBookmark size={14} />
        </ThemeIcon>
        <Text size="sm" fw={600}>
          {sources.length} Sources Referenced
        </Text>
      </Group>
    </Accordion.Control>
    
    <Accordion.Panel>
      <Stack gap="xs">
        {sources.map((source, idx) => (
          <Paper
            key={idx}
            p="sm"
            withBorder
            radius="md"
            className={styles.sourceCard}
          >
            <Group justify="space-between" wrap="nowrap">
              <Group gap="sm">
                <ThemeIcon color="green" variant="light" size="md">
                  <IconFile size={18} />
                </ThemeIcon>
                
                <div style={{ flex: 1 }}>
                  <Text size="sm" fw={600} lineClamp={1}>
                    {source.filename}
                  </Text>
                  <Group gap={8} mt={2}>
                    {source.pageRange && (
                      <Badge size="xs" variant="light" color="gray">
                        {source.pageRange}
                      </Badge>
                    )}
                    {source.relevanceScore && (
                      <Badge
                        size="xs"
                        variant="light"
                        color={getScoreColor(source.relevanceScore)}
                      >
                        {(source.relevanceScore * 100).toFixed(0)}%
                      </Badge>
                    )}
                  </Group>
                </div>
              </Group>
              
              <ActionIcon
                variant="subtle"
                size="sm"
                onClick={() => viewSource(source.id)}
              >
                <IconExternalLink size={16} />
              </ActionIcon>
            </Group>
            
            {source.excerpt && (
              <Text size="xs" c="dimmed" mt="sm" lineClamp={2}>
                "{source.excerpt}"
              </Text>
            )}
          </Paper>
        ))}
      </Stack>
    </Accordion.Panel>
  </Accordion.Item>
</Accordion>
```

**样式**：
```css
.sourceCard {
  background: white;
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;
  cursor: pointer;
}

.sourceCard:hover {
  border-color: var(--color-source);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15);
  transform: translateY(-1px);
}
```

---

### 5. Retrieval Steps（检索步骤 - Dev 模式）

```tsx
<Accordion variant="contained" mt="md">
  <Accordion.Item value="retrieval">
    <Accordion.Control>
      <Group gap="xs">
        <ThemeIcon size="sm" color="orange" variant="light">
          <IconBug size={14} />
        </ThemeIcon>
        <Text size="sm" fw={600}>
          Retrieval Pipeline (Dev Mode)
        </Text>
      </Group>
    </Accordion.Control>
    
    <Accordion.Panel>
      <Timeline
        active={steps.length}
        bulletSize={28}
        lineWidth={2}
        color="orange"
      >
        {steps.map((step, idx) => (
          <Timeline.Item
            key={idx}
            bullet={<Text size="xs" fw={700}>{idx + 1}</Text>}
            title={
              <Group gap="xs">
                <Text size="sm" fw={600}>{step.title}</Text>
                <Badge size="xs" variant="light" color="gray">
                  {step.duration}ms
                </Badge>
              </Group>
            }
          >
            <Text size="sm" c="dimmed" mb="xs">
              {step.description}
            </Text>
            
            {/* Step Data Visualization */}
            {step.type === 'vector_search' && (
              <VectorSearchResults results={step.data} />
            )}
            
            {step.type === 'rerank' && (
              <RerankResults results={step.data} />
            )}
            
            {step.type === 'context_assembly' && (
              <ContextAssembly data={step.data} />
            )}
          </Timeline.Item>
        ))}
      </Timeline>
    </Accordion.Panel>
  </Accordion.Item>
</Accordion>
```

---

## 🗂️ 文件结构（简化）

```
src/pages/retrieval/
├── RetrievalPage.tsx                    # 主页面
├── RetrievalPage.module.css             # 主样式
├── components/
│   ├── ConversationList/                # 左侧对话列表
│   │   ├── ConversationList.tsx
│   │   └── ConversationList.module.css
│   ├── ChatArea/                        # 聊天区域
│   │   ├── ChatArea.tsx
│   │   ├── ChatArea.module.css
│   │   ├── UserMessage.tsx
│   │   ├── AIMessage.tsx
│   │   └── Message.module.css
│   ├── SourceReferences/                # 来源引用
│   │   ├── SourceReferences.tsx
│   │   └── SourceReferences.module.css
│   ├── RetrievalSteps/                  # 检索步骤（Dev）
│   │   ├── RetrievalSteps.tsx
│   │   ├── VectorSearchResults.tsx
│   │   └── RerankResults.tsx
│   ├── InputArea/                       # 输入区域
│   │   ├── InputArea.tsx
│   │   ├── InputArea.module.css
│   │   └── BottomToolbar.tsx           # 底部工具栏 ⭐
│   └── ThinkingIndicator/               # 思考指示器
│       └── ThinkingIndicator.tsx
├── hooks/
│   ├── useChat.ts
│   ├── useConversations.ts
│   └── useRetrievalSettings.ts
└── types.ts
```

---

## 🎯 实现优先级

### Phase 1: 基础布局和输入 ⭐
- [ ] 两栏布局（左侧对话列表 + 右侧聊天区）
- [ ] 底部输入框（固定）
- [ ] 底部工具栏（模式切换、模型选择、dataset 选择）
- [ ] 基础消息气泡

### Phase 2: 来源引用
- [ ] Source References 组件
- [ ] 折叠/展开功能
- [ ] 点击查看详情

### Phase 3: Dev 模式
- [ ] Retrieval Steps Timeline
- [ ] 每个步骤的数据可视化
- [ ] 性能指标展示

### Phase 4: 高级功能
- [ ] 联网搜索
- [ ] 思考模式
- [ ] 对话历史管理

---

## 🎨 视觉设计细节（浅色主题）

### 页面背景
```css
.page {
  background: linear-gradient(
    180deg,
    #F8FAFC 0%,
    #F1F5F9 100%
  );
  min-height: 100vh;
}
```

### 卡片阴影
```css
.card {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

.card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}
```

### 输入框聚焦
```css
.textarea:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

---

## ✅ 关键改进点

1. **✅ 浅色主题** - 专业、清爽的浅色配色
2. **✅ 底部工具栏** - 所有控制集中在输入框下方，类似图片参考
3. **✅ 简化布局** - 去掉右侧栏，改为两栏布局
4. **✅ 模型选择器** - 放在底部工具栏，方便切换
5. **✅ 功能开关** - 联网搜索、思考模式都在底部，一目了然
6. **✅ Dataset 选择** - 右下角位置，不干扰主要交互

---

## 📊 最终效果预览

```
Input Area:
┌────────────────────────────────────────────────────────┐
│ [📎] Type your message...                   [🎤] [▶️] │
├────────────────────────────────────────────────────────┤
│ [🏠] [🔧Dev] [gpt-4o-mini ▼] [🌐] [🧠] [Dataset ▼]   │
└────────────────────────────────────────────────────────┘
```

这个设计完全符合你的需求：
- ✅ 浅色模式
- ✅ 底部工具栏（类似参考图）
- ✅ Dev/Production 模式切换
- ✅ 模型选择器
- ✅ 功能开关（联网、思考）
- ✅ Dataset 选择

准备好开始实现了吗？
