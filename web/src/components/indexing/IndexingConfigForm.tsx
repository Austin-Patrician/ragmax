import { useState, useEffect } from 'react'
import {
  Accordion,
  Box,
  Select,
  Slider,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core'
import type { ChunkerType, IndexingConfig, ParserType } from '@/types/indexing'
import {
  CHUNKER_INFO,
  DEFAULT_CHUNK_OVERLAP,
  DEFAULT_CHUNK_SIZE,
  DEFAULT_TOKENIZER,
  INDEXING_PRESETS,
  PARSER_INFO,
} from '@/config/indexing-presets'

type IndexingConfigFormProps = {
  value: IndexingConfig
  onChange: (config: IndexingConfig) => void
}

export function IndexingConfigForm({ value, onChange }: IndexingConfigFormProps) {
  const [preset, setPreset] = useState<string>('custom')
  const [showAdvanced, setShowAdvanced] = useState(false)

  // 检测当前配置是否匹配某个预设
  useEffect(() => {
    const matchedPreset = Object.entries(INDEXING_PRESETS).find(
      ([_, presetConfig]) =>
        JSON.stringify(presetConfig.config.chunker) === JSON.stringify(value.chunker) &&
        JSON.stringify(presetConfig.config.chunk_config) === JSON.stringify(value.chunk_config)
    )
    setPreset(matchedPreset ? matchedPreset[0] : 'custom')
  }, [value])

  const handlePresetChange = (presetKey: string | null) => {
    if (!presetKey) return
    setPreset(presetKey)
    if (presetKey !== 'custom' && presetKey in INDEXING_PRESETS) {
      onChange(INDEXING_PRESETS[presetKey as keyof typeof INDEXING_PRESETS].config)
    }
  }

  const handleParserChange = (parser: string | null) => {
    if (!parser) return
    const nextConfig: IndexingConfig = { ...value }
    if (parser === 'auto') {
      delete nextConfig.parser
    } else {
      nextConfig.parser = parser as ParserType
    }
    onChange(nextConfig)
  }

  const handleChunkerChange = (chunker: string | null) => {
    if (!chunker) return
    const defaultConfig = INDEXING_PRESETS.default.config.chunk_config ?? {
      chunk_size: DEFAULT_CHUNK_SIZE,
      chunk_overlap: DEFAULT_CHUNK_OVERLAP,
      tokenizer_model: DEFAULT_TOKENIZER,
    }
    onChange({
      ...value,
      chunker: chunker as ChunkerType,
      chunk_config: {
        ...defaultConfig,
        ...value.chunk_config,
      },
    })
    setPreset('custom')
  }

  const handleChunkConfigChange = (key: string, val: any) => {
    onChange({
      ...value,
      chunk_config: {
        ...value.chunk_config,
        [key]: val,
      },
    })
    setPreset('custom')
  }

  const handleParserConfigChange = (key: string, val: any) => {
    onChange({
      ...value,
      parser_config: {
        ...value.parser_config,
        [key]: val,
      },
    })
  }

  const chunker = value.chunker || 'fixed_token'
  const parser = value.parser || ('auto' as const)
  const chunkSize = value.chunk_config?.chunk_size ?? DEFAULT_CHUNK_SIZE
  const chunkOverlap = value.chunk_config?.chunk_overlap ?? DEFAULT_CHUNK_OVERLAP

  // 构建预设选项
  const presetOptions = [
    { value: 'custom', label: '自定义配置' },
    ...Object.entries(INDEXING_PRESETS).map(([key, preset]) => ({
      value: key,
      label: preset.name,
    })),
  ]

  // 构建Parser选项
  const parserOptions = Object.entries(PARSER_INFO).map(([key, info]) => ({
    value: key,
    label: info.name,
  }))

  // 构建Chunker选项
  const chunkerOptions = Object.entries(CHUNKER_INFO).map(([key, info]) => ({
    value: key,
    label: info.name,
  }))

  return (
    <Stack gap="md">
      {/* 配置预设 */}
      <Select
        label="配置预设"
        description="选择预设配置或自定义"
        placeholder="选择预设"
        data={presetOptions}
        value={preset}
        onChange={handlePresetChange}
      />

      {/* Parser选择 */}
      <Select
        label="Parser"
        description="文档解析器（Auto会根据文件类型自动选择）"
        placeholder="选择Parser"
        data={parserOptions}
        value={parser}
        onChange={handleParserChange}
      />

      {/* LlamaParse特定配置 */}
      {parser === 'llamaparse' && (
        <Select
          label="LlamaParse Tier"
          placeholder="选择tier"
          data={[
            { value: 'free', label: 'Free' },
            { value: 'premium', label: 'Premium' },
          ]}
          value={value.parser_config?.tier || 'free'}
          onChange={(val) => handleParserConfigChange('tier', val)}
        />
      )}

      {/* MinerU特定配置 */}
      {parser === 'mineru' && (
        <Stack gap="xs">
          <Switch
            label="启用表格识别"
            checked={value.parser_config?.enable_table ?? true}
            onChange={(e) => handleParserConfigChange('enable_table', e.currentTarget.checked)}
          />
          <Switch
            label="启用公式识别"
            checked={value.parser_config?.enable_formula ?? true}
            onChange={(e) => handleParserConfigChange('enable_formula', e.currentTarget.checked)}
          />
        </Stack>
      )}

      {/* Chunker选择 */}
      <Box>
        <Select
          label="Chunking Strategy"
          description="分块策略"
          placeholder="选择策略"
          data={chunkerOptions}
          value={chunker}
          onChange={handleChunkerChange}
        />
        {CHUNKER_INFO[chunker as ChunkerType] && (
          <Text size="xs" c="dimmed" mt={4}>
            {CHUNKER_INFO[chunker as ChunkerType].description}
          </Text>
        )}
      </Box>

      {/* Chunk Size */}
      <Box>
        <Text size="sm" fw={500} mb={4}>
          Chunk Size (tokens): {chunkSize}
        </Text>
        <Slider
          value={chunkSize}
          onChange={(val) => handleChunkConfigChange('chunk_size', val)}
          min={100}
          max={2000}
          step={100}
          marks={[
            { value: 100, label: '100' },
            { value: 500, label: '500' },
            { value: 1000, label: '1000' },
            { value: 1500, label: '1500' },
            { value: 2000, label: '2000' },
          ]}
        />
        <Text size="xs" c="dimmed" mt={4}>
          每个chunk的Token数量
        </Text>
      </Box>

      {/* Chunk Overlap */}
      <Box>
        <Text size="sm" fw={500} mb={4}>
          Chunk Overlap (tokens): {chunkOverlap}
        </Text>
        <Slider
          value={chunkOverlap}
          onChange={(val) => handleChunkConfigChange('chunk_overlap', val)}
          min={0}
          max={500}
          step={50}
          marks={[
            { value: 0, label: '0' },
            { value: 100, label: '100' },
            { value: 200, label: '200' },
            { value: 300, label: '300' },
            { value: 500, label: '500' },
          ]}
        />
        <Text size="xs" c="dimmed" mt={4}>
          相邻chunk的重叠Token数
        </Text>
      </Box>

      {/* Semantic Vector特定配置 */}
      {chunker === 'semantic_vector' && (
        <TextInput
          label="Similarity Threshold (%)"
          description="语义相似度阈值百分位 (0-100)，越高越保守"
          type="number"
          value={value.chunk_config?.similarity_threshold_percentile ?? 75}
          onChange={(e) =>
            handleChunkConfigChange('similarity_threshold_percentile', parseInt(e.target.value))
          }
          min={0}
          max={100}
          step={5}
        />
      )}

      {/* Table Aware特定配置 */}
      {chunker === 'table_aware' && (
        <Switch
          label="重复表头（每个chunk包含表头）"
          checked={value.chunk_config?.repeat_table_header ?? true}
          onChange={(e) => handleChunkConfigChange('repeat_table_header', e.currentTarget.checked)}
        />
      )}

      {/* Section Aware特定配置 */}
      {chunker === 'section_aware' && (
        <Switch
          label="保留章节标题"
          checked={value.chunk_config?.keep_headings ?? true}
          onChange={(e) => handleChunkConfigChange('keep_headings', e.currentTarget.checked)}
        />
      )}

      {/* 高级选项 */}
      <Accordion value={showAdvanced ? 'advanced' : null} onChange={(val) => setShowAdvanced(val === 'advanced')}>
        <Accordion.Item value="advanced">
          <Accordion.Control>高级选项</Accordion.Control>
          <Accordion.Panel>
            <Stack gap="md">
              <Select
                label="Tokenizer Model"
                description="Token编码模型"
                data={[
                  { value: 'cl100k_base', label: 'cl100k_base (GPT-4, GPT-3.5-turbo)' },
                  { value: 'p50k_base', label: 'p50k_base (GPT-3, Codex)' },
                  { value: 'r50k_base', label: 'r50k_base (GPT-2)' },
                ]}
                value={value.chunk_config?.tokenizer_model || DEFAULT_TOKENIZER}
                onChange={(val) => handleChunkConfigChange('tokenizer_model', val)}
              />

              <Switch
                label="保存Pipeline Artifacts（用于调试和分析）"
                checked={value.capture_artifacts ?? false}
                onChange={(e) =>
                  onChange({
                    ...value,
                    capture_artifacts: e.currentTarget.checked,
                  })
                }
              />
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  )
}
