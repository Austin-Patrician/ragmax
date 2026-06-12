# IndexingConfigForm - Mantine版本

## 更新完成 ✅

已将 `IndexingConfigForm` 从Material-UI重写为**Mantine v9**框架。

---

## 使用的Mantine组件

### 核心组件
- `Stack` - 垂直布局容器（替代MUI的Box + flexDirection）
- `Select` - 下拉选择器（替代MUI的Select + MenuItem）
- `Slider` - 滑块（替代MUI的Slider）
- `Switch` - 开关（替代MUI的Switch）
- `TextInput` - 文本输入（替代MUI的TextField）
- `Accordion` - 手风琴折叠面板（替代MUI的Accordion）
- `Box` - 通用容器
- `Group` - 水平布局容器
- `Text` - 文本组件（替代MUI的Typography）

### 组件特点（Mantine v9）
- 使用 `gap` 而不是 `spacing`
- 使用 `c="dimmed"` 设置灰色文本
- 使用 `fw={500}` 设置字重
- Select组件使用 `data` prop接收选项数组
- Accordion使用受控模式（value + onChange）

---

## 代码对比

### Material-UI (旧)
```tsx
<FormControl fullWidth>
  <InputLabel>Parser</InputLabel>
  <Select value={parser} onChange={handleChange} label="Parser">
    <MenuItem value="auto">
      <ListItemText primary="Auto" secondary="根据文件类型" />
    </MenuItem>
  </Select>
  <FormHelperText>帮助文本</FormHelperText>
</FormControl>
```

### Mantine (新)
```tsx
<Select
  label="Parser"
  description="帮助文本"
  placeholder="选择Parser"
  data={[{ value: 'auto', label: 'Auto' }]}
  value={parser}
  onChange={handleChange}
/>
```

---

## 功能保持一致

✅ **所有功能完全一致**：
- 配置预设选择
- Parser选择和配置
- Chunker选择和配置
- Chunk Size/Overlap滑块
- 特定chunker配置
- 高级选项折叠面板
- 自动检测预设匹配

---

## 视觉效果

Mantine默认样式更现代，与你的系统风格一致：
- 更柔和的边框和阴影
- 更好的间距和对齐
- 更流畅的动画
- 更好的可访问性

---

## 依赖

项目已安装：
- `@mantine/core@^9.3.0`
- `@mantine/hooks@^9.3.0`
- `@mantine/notifications@^9.3.0`

无需额外安装依赖。

---

## 使用示例

```tsx
import { IndexingConfigForm } from '@/components/indexing/IndexingConfigForm'
import { useState } from 'react'
import { INDEXING_PRESETS } from '@/config/indexing-presets'

function MyComponent() {
  const [config, setConfig] = useState(INDEXING_PRESETS.default.config)
  
  return (
    <IndexingConfigForm 
      value={config} 
      onChange={setConfig} 
    />
  )
}
```

---

## 测试清单

启动前端后测试：
- [ ] 预设选择工作正常
- [ ] Parser选择和特定配置显示
- [ ] Chunker选择和特定配置显示
- [ ] 滑块交互流畅
- [ ] 高级选项展开/折叠
- [ ] 所有状态更新正确

---

## 完成！

✅ IndexingConfigForm现在使用Mantine v9
✅ 与项目UI框架一致
✅ 所有功能保持完整
✅ 准备测试！
