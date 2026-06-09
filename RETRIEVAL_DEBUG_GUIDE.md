# RetrievalPage 调试指南

## 快速验证步骤

1. **启动开发服务器**：
```bash
cd web
npm run dev
```

2. **访问页面**：
打开浏览器访问 `http://localhost:5174/retrieval`

3. **检查是否有问题**：

### 如果页面完全空白：
打开浏览器控制台（F12），查看是否有错误信息。

### 如果样式错乱：
可能是 CSS 变量未正确加载。检查 `web/src/index.css` 是否包含这些变量：
```css
--color-primary: #6366F1;
--color-surface: #FFFFFF;
--color-background: #F9FAFB;
--color-border: #E5E7EB;
--color-text-primary: #111827;
```

### 如果组件未显示：
1. 检查是否有 TypeScript 错误：`npm run build`
2. 查看浏览器控制台的 React 错误

## 当前页面应该显示：

### 左侧边栏
- 顶部："新建对话"按钮（蓝色，带 + 图标）
- 中间：搜索框
- 下方：对话列表（当前有一个示例对话 "初次问候对话"）

### 右侧主区域
- 顶部：页眉（菜单按钮 + 对话标题）
- 中间：空状态（机器人图标 + "Hi! 👋 选择数据集并在下方输入消息"）
- 底部：输入框区域
  - 大文本框
  - 右侧发送按钮（蓝色圆角）
  - 底部工具栏（+ 图标、数据集选择器、搜索/灯泡图标、设置图标、模型名称）

## 如果仍然不可用

请告诉我：
1. 浏览器控制台显示什么错误？
2. 页面是完全空白，还是有部分显示？
3. 网络请求是否正常（Network 标签）？

## 临时回退方案

如果新界面有问题，可以使用 git 回退到之前的版本：
```bash
git checkout HEAD -- web/src/pages/retrieval/RetrievalPage.tsx
git checkout HEAD -- web/src/pages/retrieval/RetrievalPage.module.css
```

然后重新启动开发服务器。
