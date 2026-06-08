# Enhanced Parser Design Plan

## 目标
设计并实现一个更专业、稳定、高质量的 Parser 系统，替代当前简单的 `blocks_from_text` 启发式解析。

## 当前问题分析

### 1. **核心问题：`blocks_from_text` 过于简单**
```python
# 当前实现：仅靠 \n\n 分段
segments = [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]
```

**缺陷**：
- 无法识别复杂的文档结构（列表、引用、代码块）
- Heading 识别规则有限（仅 `#`、数字编号、中文章节）
- Table 识别依赖简单标记（`|`、`\t`、HTML），漏识率高
- 没有上下文感知（前后段落关系）
- 没有处理 Markdown/HTML 等结构化格式

### 2. **现有架构优势**
- **清晰的接口**：`SourceParser` protocol 定义良好
- **灵活的注册机制**：`SourceParserRegistry` 支持多 parser
- **分层设计**：parse → analyze → chunk → enrich 职责清晰
- **已有基础设施**：LlamaParse 和 SimpleDirectoryReader 已集成

## 设计方案

### **方案 A：增强型启发式 Parser（推荐）**

#### 设计理念
保持轻量级、零外部 API 依赖，但大幅提升识别能力。

#### 核心组件

##### 1. **AdvancedTextParser**
替代 `HeuristicSourceParser`，使用多阶段解析：

**阶段 1：格式检测**
- 检测文本是否为 Markdown、HTML、纯文本
- 根据格式选择解析策略

**阶段 2：结构化解析**
- **Markdown**：使用成熟库（如 `mistune` 或 `markdown-it-py`）解析 AST
- **HTML**：使用 `beautifulsoup4` 或 `lxml` 解析 DOM
- **纯文本**：使用增强启发式规则

**阶段 3：Block 构建**
- 将 AST/DOM 节点转换为 `ContentBlock`
- 保留层级关系（section_hint）
- 识别更多 block 类型

##### 2. **增强的 Block Type 识别**

支持的 Block Types：
```python
class BlockType(StrEnum):
    TEXT = "text"              # 普通段落
    HEADING = "heading"        # 标题（H1-H6）
    TABLE = "table"            # 表格
    LIST = "list"              # 列表（有序/无序）
    CODE = "code"              # 代码块
    QUOTE = "quote"            # 引用块
    IMAGE = "image"            # 图片（保留）
    OCR = "ocr"                # OCR 文本（保留）
    DIVIDER = "divider"        # 分隔线
```

##### 3. **智能 Heading 层级推断**

改进的 heading 检测：
```python
def detect_heading(text: str, context: ParsingContext) -> tuple[bool, int]:
    """
    返回: (is_heading, level)
    
    检测规则：
    1. Markdown: # 符号（1-6个）
    2. 数字编号: 1., 1.1, 1.1.1 等
    3. 中文章节: 第X章/节/部分
    4. 全大写短文本（英文）
    5. 字体特征（如果有元数据）
    6. 上下文线索：
       - 前后有空行
       - 长度较短（<80 字符）
       - 无结束标点
    """
```

##### 4. **表格识别增强**

多种表格格式：
```python
def detect_table(lines: list[str]) -> TableInfo | None:
    """
    支持格式：
    1. Markdown 表格：| col1 | col2 |
    2. 制表符分隔：col1\tcol2
    3. 空格对齐（固定宽度）：
       Name      Age    City
       ----      ---    ----
       Alice     25     NYC
    4. HTML 表格：<table>...</table>
    5. 简单网格（ASCII art）：
       +-------+-----+
       | Name  | Age |
       +-------+-----+
    """
```

##### 5. **列表识别**

支持：
- 无序列表：`-`, `*`, `•`
- 有序列表：`1.`, `a.`, `i.`, `(1)`, `①`
- 嵌套列表（缩进检测）
- 任务列表：`- [ ]`, `- [x]`

#### 实现结构

```
src/ragmax/infrastructure/indexing/parsers/
├── advanced/
│   ├── __init__.py
│   ├── parser.py                    # AdvancedTextParser 主类
│   ├── format_detector.py           # 格式检测（Markdown/HTML/Plain）
│   ├── markdown_parser.py           # Markdown AST 解析
│   ├── html_parser.py               # HTML DOM 解析
│   ├── plain_text_parser.py         # 增强纯文本解析
│   ├── block_builder.py             # 将 AST/DOM 转为 ContentBlock
│   ├── heading_detector.py          # 高级 heading 识别
│   ├── table_detector.py            # 多格式表格识别
│   ├── list_detector.py             # 列表识别
│   └── context.py                   # ParsingContext 上下文管理
├── block_parsing.py                 # 保留兼容性
└── heuristic_source_parser.py       # 标记为 deprecated
```

#### 依赖添加

```toml
# pyproject.toml
dependencies = [
    # ... existing ...
    "mistune>=3.0.0",                # Markdown parser
    "beautifulsoup4>=4.12.0",        # HTML parser (optional)
    "lxml>=5.0.0",                   # Fast XML/HTML parser (optional)
]
```

#### API 设计

```python
# advanced/parser.py
class AdvancedTextParser:
    """
    高级文本解析器，支持 Markdown、HTML 和增强纯文本解析。
    """
    parser_name = "advanced_text_parser"
    parser_version = "v2.0"
    
    async def parse(
        self,
        source: SourceInput,
        options: Mapping[str, Any] | None = None,
    ) -> SourceDocument:
        """
        Options:
        - format: 'auto' | 'markdown' | 'html' | 'plain'  (default: 'auto')
        - strict_headings: bool  (default: False)
        - detect_tables: bool  (default: True)
        - detect_lists: bool  (default: True)
        - preserve_code_blocks: bool  (default: True)
        - min_heading_length: int  (default: 3)
        - max_heading_length: int  (default: 80)
        """
        pass

# advanced/context.py
@dataclass
class ParsingContext:
    """解析上下文，用于跨 block 的状态管理"""
    format: str  # 'markdown' | 'html' | 'plain'
    current_section_path: list[str]
    current_heading_level: int
    last_block_type: BlockType | None
    options: dict[str, Any]
```

---

### **方案 B：集成第三方专业 Parser（备选）**

#### 选项 1：使用 `unstructured`

优势：
- 专业的文档解析库
- 支持 PDF、Word、HTML、Markdown 等多种格式
- 自动检测文档结构
- 活跃维护

缺点：
- 依赖较重（需要 `libmagic`、`poppler` 等系统库）
- Windows 安装复杂
- 可能需要额外配置

#### 选项 2：使用 `docling`

优势：
- IBM Research 出品，专注于文档理解
- 支持复杂布局分析
- 可以识别页眉、页脚、多栏等

缺点：
- 相对较新，社区较小
- 依赖较重

#### 方案 B 不推荐原因
1. **依赖复杂**：Windows 环境下安装困难
2. **过度设计**：对于文本/Markdown 输入，这些库提供的能力超过需求
3. **性能开销**：重量级库解析简单文本会有不必要的延迟
4. **已有 LlamaParse**：复杂 PDF 已经有 LlamaParse 处理

---

## 推荐方案：方案 A（增强型启发式 Parser）

### 实现步骤

#### Phase 1: 核心基础设施
1. 创建 `advanced/` 目录结构
2. 实现 `ParsingContext` 和基础接口
3. 实现 `FormatDetector`（检测 Markdown/HTML/Plain）
4. 编写单元测试

#### Phase 2: Markdown 支持
1. 集成 `mistune` 解析 Markdown AST
2. 实现 `MarkdownParser`（AST → ContentBlock）
3. 支持：headings, lists, tables, code blocks, quotes
4. 测试常见 Markdown 文档

#### Phase 3: 纯文本增强
1. 实现 `HeadingDetector`（多规则 heading 识别）
2. 实现 `TableDetector`（多格式表格识别）
3. 实现 `ListDetector`（列表识别）
4. 实现 `PlainTextParser`（组合各检测器）
5. 测试各种纯文本格式

#### Phase 4: HTML 支持（可选）
1. 集成 `beautifulsoup4` 或 `lxml`
2. 实现 `HTMLParser`（DOM → ContentBlock）
3. 测试 HTML 文档

#### Phase 5: 集成与测试
1. 在 `SourceParserRegistry` 中注册 `AdvancedTextParser`
2. 更新 `inline_parser` 配置指向新 parser
3. 端到端测试
4. 性能测试
5. 向后兼容性测试（保留 `HeuristicSourceParser` 作为 fallback）

#### Phase 6: 质量保障
1. 添加质量指标：
   - Block type 识别准确率
   - Heading level 准确率
   - Table 召回率
2. 添加边界情况测试：
   - 空文档
   - 超长文档
   - 格式错误文档
   - 混合格式文档
3. 性能基准测试

---

## 测试策略

### 1. **单元测试**（80+ 测试用例）

```python
# tests/unit/test_heading_detector.py
def test_markdown_heading_detection():
    assert detect_heading("# Title") == (True, 1)
    assert detect_heading("## Subtitle") == (True, 2)

def test_numbered_heading_detection():
    assert detect_heading("1. Introduction") == (True, 1)
    assert detect_heading("1.2.3 Details") == (True, 3)

def test_chinese_heading_detection():
    assert detect_heading("第一章 引言") == (True, 1)
    assert detect_heading("第二节 方法") == (True, 2)

def test_uppercase_heading_detection():
    assert detect_heading("INTRODUCTION") == (True, 2)
    
def test_false_positives():
    assert detect_heading("This is a normal sentence.") == (False, 0)
    assert detect_heading("1. Item in a list with more text") == (False, 0)

# tests/unit/test_table_detector.py
def test_markdown_table():
    table = """
    | Name | Age |
    |------|-----|
    | Alice| 25  |
    """
    assert is_table(table) == True

def test_tab_delimited_table():
    table = "Name\tAge\nAlice\t25"
    assert is_table(table) == True

def test_fixed_width_table():
    table = """
    Name      Age
    ----      ---
    Alice     25
    """
    assert is_table(table) == True

# tests/unit/test_list_detector.py
def test_unordered_list():
    assert is_list_item("- Item 1") == True
    assert is_list_item("* Item 2") == True

def test_ordered_list():
    assert is_list_item("1. First") == True
    assert is_list_item("a. First") == True

def test_nested_list():
    items = ["- Level 1", "  - Level 2", "    - Level 3"]
    assert get_list_level(items[0]) == 1
    assert get_list_level(items[1]) == 2
```

### 2. **集成测试**（20+ 测试用例）

```python
# tests/integration/test_advanced_parser.py
async def test_markdown_document_parsing():
    source = SourceInput(
        source_id="test-1",
        notebook_id="nb-1",
        filename="doc.md",
        media_type="text/markdown",
        text=MARKDOWN_SAMPLE,
    )
    
    parser = AdvancedTextParser()
    document = await parser.parse(source)
    
    assert len(document.blocks) > 0
    block_types = {block.block_type for block in document.blocks}
    assert BlockType.HEADING in block_types
    assert BlockType.TEXT in block_types

async def test_complex_document_with_all_block_types():
    # 包含 heading, text, table, list, code, quote
    text = """
    # Main Title
    
    Introduction paragraph.
    
    ## Features
    
    - Feature 1
    - Feature 2
    
    ### Data
    
    | Column 1 | Column 2 |
    |----------|----------|
    | Value 1  | Value 2  |
    
    ```python
    def hello():
        print("world")
    ```
    
    > This is a quote.
    """
    
    source = SourceInput(
        source_id="test-2",
        notebook_id="nb-1",
        filename="doc.md",
        media_type="text/markdown",
        text=text,
    )
    
    document = await parser.parse(source)
    
    block_types = [block.block_type for block in document.blocks]
    assert BlockType.HEADING in block_types
    assert BlockType.TEXT in block_types
    assert BlockType.TABLE in block_types
    assert BlockType.LIST in block_types
    assert BlockType.CODE in block_types
    assert BlockType.QUOTE in block_types
```

### 3. **端到端测试**（10+ 测试用例）

```python
# tests/e2e/test_enhanced_parsing_pipeline.py
async def test_markdown_source_full_pipeline(persisted_client):
    # 1. Create source
    create_response = persisted_client.post(
        "/api/v1/sources",
        json={
            "notebook_id": "nb-1",
            "filename": "guide.md",
            "media_type": "text/markdown",
            "text": MARKDOWN_GUIDE,
        },
    )
    assert create_response.status_code == 201
    
    # 2. Preview indexing
    preview_response = persisted_client.post(
        f"/api/v1/sources/{source_id}/index/preview",
        json={"profile_name": "section_pdf"},
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()
    
    # Verify blocks
    assert preview["summary"]["block_types"]["heading"] > 0
    assert preview["summary"]["block_types"]["text"] > 0
    
    # 3. Run indexing
    index_response = persisted_client.post(
        f"/api/v1/sources/{source_id}/index",
        json={"profile_name": "section_pdf"},
    )
    assert index_response.status_code == 200
    
    # 4. Verify node structure
    nodes = index_response.json()["nodes"]
    # Verify section_path is populated correctly
    assert any(node["section_path"] for node in nodes)
```

### 4. **性能测试**

```python
# tests/performance/test_parser_performance.py
@pytest.mark.benchmark
def test_large_document_parsing_performance():
    """测试解析 10000 行文档的性能"""
    text = generate_large_markdown(lines=10000)
    
    start = time.perf_counter()
    document = await parser.parse(source)
    elapsed = time.perf_counter() - start
    
    assert elapsed < 2.0  # 应在 2 秒内完成
    assert len(document.blocks) > 100

@pytest.mark.benchmark
def test_parser_comparison():
    """对比新旧 parser 性能"""
    old_elapsed = benchmark_old_parser(text)
    new_elapsed = benchmark_new_parser(text)
    
    # 新 parser 不应慢于旧 parser 超过 50%
    assert new_elapsed < old_elapsed * 1.5
```

### 5. **质量指标测试**

```python
# tests/quality/test_block_quality.py
def test_heading_recognition_accuracy():
    """使用标注数据集测试 heading 识别准确率"""
    test_cases = load_labeled_dataset("headings")
    
    correct = 0
    for text, expected_is_heading, expected_level in test_cases:
        is_heading, level = detect_heading(text, context)
        if is_heading == expected_is_heading and level == expected_level:
            correct += 1
    
    accuracy = correct / len(test_cases)
    assert accuracy > 0.90  # 目标：90% 以上准确率

def test_table_recall():
    """测试表格召回率（不漏检）"""
    test_cases = load_labeled_dataset("tables")
    
    detected = 0
    for text, is_table in test_cases:
        if is_table and detect_table(text):
            detected += 1
    
    recall = detected / sum(1 for _, is_table in test_cases if is_table)
    assert recall > 0.85  # 目标：85% 以上召回率
```

---

## 质量保障

### 1. **代码质量**
- 类型注解覆盖 100%
- Docstring 覆盖所有公共 API
- 遵循项目 Ruff 规则
- 代码复杂度控制（McCabe < 10）

### 2. **测试覆盖**
- 单元测试覆盖率 > 90%
- 集成测试覆盖主要流程
- 边界情况测试完善

### 3. **性能基准**
- 解析速度：1000 行/秒
- 内存占用：<100MB（10000 行文档）
- 不应显著慢于现有 parser

### 4. **向后兼容**
- 保留 `HeuristicSourceParser` 作为 fallback
- 提供配置开关切换新旧 parser
- API 接口不变

---

## 配置与部署

### 1. **环境变量**

```env
# .env
# Parser 选择
INLINE_PARSER=advanced_text_parser  # 或 inline_content_parser (旧版)

# Advanced Parser 配置
ADVANCED_PARSER_STRICT_HEADINGS=false
ADVANCED_PARSER_DETECT_TABLES=true
ADVANCED_PARSER_DETECT_LISTS=true
ADVANCED_PARSER_MIN_HEADING_LENGTH=3
ADVANCED_PARSER_MAX_HEADING_LENGTH=80
```

### 2. **注册配置**

```python
# src/ragmax/api/dependencies.py
def get_source_parser_registry() -> SourceParserRegistry:
    inline_parser = settings.INLINE_PARSER or "advanced_text_parser"
    
    return SourceParserRegistry(
        parsers={
            "simple_directory_reader": SimpleDirectoryReaderSourceParser(),
            "llamaparse": LlamaParseSourceParser(...),
            "inline_content_parser": HeuristicSourceParser(),  # 旧版，保留兼容
            "advanced_text_parser": AdvancedTextParser(),      # 新版，推荐
        },
        specs=(...),
        default_file_parser=settings.DEFAULT_FILE_PARSER,
        inline_parser=inline_parser,
    )
```

---

## 风险与缓解

### 风险 1：新 parser 引入 bug
**缓解**：
- 保留旧 parser 作为 fallback
- 提供配置开关
- 充分的测试覆盖

### 风险 2：性能下降
**缓解**：
- 性能基准测试
- 针对大文档优化
- 考虑缓存策略

### 风险 3：第三方库依赖问题
**缓解**：
- 选择成熟、维护良好的库（`mistune`）
- 锁定版本，避免破坏性更新
- HTML 支持设为可选（不强制依赖）

### 风险 4：迁移成本
**缓解**：
- 保持 API 兼容
- 分阶段推出（默认关闭 → 可选启用 → 默认启用）
- 提供迁移文档

---

## 成功指标

### 技术指标
- [ ] Heading 识别准确率 > 90%
- [ ] Table 召回率 > 85%
- [ ] List 识别准确率 > 85%
- [ ] 单元测试覆盖率 > 90%
- [ ] 解析性能：1000 行/秒
- [ ] 零破坏性变更（向后兼容）

### 业务指标
- [ ] 支持 Markdown 格式文档
- [ ] 支持复杂纯文本文档
- [ ] Block type 类型增加至 9 种
- [ ] Section path 准确率提升 50%

---

## 时间估算

- **Phase 1（基础设施）**: 4 小时
- **Phase 2（Markdown 支持）**: 6 小时
- **Phase 3（纯文本增强）**: 8 小时
- **Phase 4（HTML 支持）**: 4 小时（可选）
- **Phase 5（集成与测试）**: 6 小时
- **Phase 6（质量保障）**: 6 小时

**总计**: 30-34 小时

---

## 后续优化方向

1. **机器学习增强**
   - 使用小模型（如 DistilBERT）进行 block type 分类
   - 训练 heading level 预测模型

2. **布局分析**
   - 对于 PDF 等复杂文档，引入布局分析
   - 识别多栏、页眉页脚

3. **语义理解**
   - 段落主题分类
   - 引用关系检测
   - 实体识别

4. **自适应解析**
   - 基于用户反馈学习
   - 自动调整解析参数
