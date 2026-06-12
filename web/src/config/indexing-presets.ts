import type { ChunkerType, IndexingConfig } from '@/types/indexing'

export type IndexingPreset = {
  name: string
  description: string
  config: IndexingConfig
}

export type IndexingPresetKey = 'default' | 'research_paper' | 'technical_doc' | 'data_table'

export const INDEXING_PRESETS: Record<IndexingPresetKey, IndexingPreset> = {
  default: {
    name: '默认配置',
    description: '适合大多数场景，精确的Token级别分块',
    config: {
      chunker: 'fixed_token',
      chunk_config: {
        chunk_size: 1000,
        chunk_overlap: 100,
        tokenizer_model: 'cl100k_base',
      },
    },
  },
  research_paper: {
    name: '研究论文',
    description: '基于语义边界的智能分块，保持语义完整性',
    config: {
      chunker: 'semantic_vector',
      chunk_config: {
        chunk_size: 1000,
        chunk_overlap: 0,
        similarity_threshold_percentile: 75,
        tokenizer_model: 'cl100k_base',
      },
    },
  },
  technical_doc: {
    name: '技术文档',
    description: '保持章节结构和标题层级',
    config: {
      chunker: 'section_aware',
      chunk_config: {
        chunk_size: 800,
        chunk_overlap: 100,
        keep_headings: true,
        tokenizer_model: 'cl100k_base',
      },
    },
  },
  data_table: {
    name: '数据表格',
    description: '表格增强分块，自动恢复表头',
    config: {
      chunker: 'table_aware',
      chunk_config: {
        chunk_size: 600,
        chunk_overlap: 80,
        repeat_table_header: true,
        tokenizer_model: 'cl100k_base',
      },
    },
  },
}

export const CHUNKER_INFO: Record<ChunkerType, { name: string; description: string }> = {
  fixed_token: {
    name: 'Fixed Token',
    description: '精确的Token级别分块，适合大多数场景',
  },
  semantic_vector: {
    name: 'Semantic Vector (V策略)',
    description: '基于Embedding相似度的智能分块，在语义边界处切分',
  },
  section_aware: {
    name: 'Section Aware',
    description: '保持章节结构，适合有明确章节的文档',
  },
  table_aware: {
    name: 'Table Aware',
    description: '表格增强分块，支持表头恢复',
  },
  ocr_page: {
    name: 'OCR Page',
    description: 'OCR页面级别分块',
  },
}

export const PARSER_INFO = {
  auto: {
    name: 'Auto',
    description: '根据文件类型自动选择Parser',
  },
  simple_directory_reader: {
    name: 'Simple Reader',
    description: '本地解析器，支持常见文件格式',
  },
  llamaparse: {
    name: 'LlamaParse',
    description: '强大的云端解析器，支持复杂PDF',
  },
  mineru: {
    name: 'MinerU',
    description: '表格和公式增强解析器',
  },
}

export const DEFAULT_CHUNK_SIZE = 1000
export const DEFAULT_CHUNK_OVERLAP = 100
export const DEFAULT_TOKENIZER = 'cl100k_base'
