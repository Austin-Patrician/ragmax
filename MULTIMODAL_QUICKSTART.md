# 多模态 Parser 快速使用指南

## 前置条件

### 1. 配置 MinerU API Token
在 `.env` 文件中添加：
```bash
MINERU_API_TOKEN=your_mineru_token_here
MINERU_API_BASE_URL=https://mineru.net
MINERU_MODEL_VERSION=vlm
MINERU_ENABLE_TABLE=true
MINERU_ENABLE_FORMULA=true
```

### 2. （可选）配置 VLM 增强
如果需要图像语义增强，添加：
```bash
VLM_ENABLED=true
VLM_API_KEY=your_vlm_api_key
VLM_BASE_URL=https://your-vlm-endpoint
VLM_MODEL=qwen/qwen3-vl-32b-instruct
```

## 使用方式

### 方式 1：通过 API 上传文档

```bash
# 上传 PDF 文档，使用 mineru parser
curl -X POST http://localhost:8000/api/v1/indexing/sources \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "parser_name=mineru" \
  -F "notebook_id=your_notebook_id"
```

### 方式 2：通过前端界面

1. 进入 Indexing 页面
2. 选择文件上传
3. Parser 下拉菜单选择 "mineru"
4. 点击上传

## 输出说明

### ContentBlock 结构

#### IMAGE blocks
```python
{
  "block_type": "image",
  "text": "[Image: image_0.png]",
  "page_no": 1,
  "section_hint": ["Introduction", "Background"],
  "metadata": {
    "image_path": "/path/to/storage/source_id/images/image_0.png",
    "image_caption": ["Figure 1: System Architecture"],
    "image_footnote": ["*Simplified for clarity"],
    "content_list_index": 5,
    # VLM 增强（如果启用）
    "vlm_description": "A detailed system architecture diagram showing...",
    "entity_info": {
      "entity_name": "System Architecture Diagram",
      "entity_type": "image",
      "summary": "Shows the main components and their interactions..."
    }
  }
}
```

#### TABLE blocks
```python
{
  "block_type": "table",
  "text": "| Header1 | Header2 |\n|---------|---------|...",
  "page_no": 2,
  "metadata": {
    "table_body": "| Header1 | Header2 |...",
    "table_caption": ["Table 1: Performance Metrics"],
    "table_footnote": [],
    "content_list_index": 12
  }
}
```

#### EQUATION blocks
```python
{
  "block_type": "equation",
  "text": "E = mc^2",
  "page_no": 3,
  "metadata": {
    "equation_latex": "E = mc^2",
    "equation_format": "latex",
    "content_list_index": 18
  }
}
```

## 验证步骤

### 1. 检查 Parser 是否注册成功

```bash
curl http://localhost:8000/api/v1/indexing/parsers
```

应该看到 `mineru` 在列表中（前提是配置了 MINERU_API_TOKEN）。

### 2. 测试基础解析

上传一个包含图像的 PDF，检查返回的 blocks：

```bash
# 创建 source
curl -X POST http://localhost:8000/api/v1/indexing/sources \
  -F "file=@test.pdf" \
  -F "parser_name=mineru" \
  -F "notebook_id=test"

# 查看解析结果
curl http://localhost:8000/api/v1/indexing/sources/{source_id}
```

### 3. 测试 VLM 增强

启用 VLM 后上传文档，检查 IMAGE blocks 的 metadata 是否包含 `vlm_description` 字段。

## 故障排查

### MinerU API 调用失败

**症状**：上传文档时报错 "MinerU API error"

**检查**：
1. `MINERU_API_TOKEN` 是否正确
2. API endpoint 是否可访问：`curl https://mineru.net/api/v4/health`
3. 文件大小是否超限（200MB）
4. 页数是否超限（200 页）

### VLM 增强不生效

**症状**：IMAGE blocks 没有 `vlm_description`

**检查**：
1. `VLM_ENABLED=true` 是否设置
2. `VLM_API_KEY` 是否配置
3. 查看日志是否有 VLM 调用错误（会降级，不阻塞流程）

### 图像文件找不到

**症状**：image_path 路径不存在

**检查**：
1. `SOURCE_STORAGE_DIR` 权限是否正确
2. 磁盘空间是否足够
3. 检查 `{SOURCE_STORAGE_DIR}/{source_id}/images/` 目录

## 性能调优

### 1. 调整 MinerU 轮询间隔

```bash
MINERU_POLLING_INTERVAL=1.0  # 更快的状态检查（默认 2.0）
```

### 2. 调整 VLM 并发数

修改 `modal_processor.py` 中的 `max_concurrent` 参数（默认 5）。

### 3. 禁用不需要的功能

```bash
MINERU_ENABLE_TABLE=false    # 不解析表格
MINERU_ENABLE_FORMULA=false  # 不解析公式
VLM_ENABLED=false            # 禁用 VLM 增强
```

## 下一步

1. 测试多模态检索（在 Retrieval 页面搜索图像相关内容）
2. 查看 Indexing artifacts（观察各阶段输出）
3. 根据需求调整 Context 提取配置（window size、mode 等）
