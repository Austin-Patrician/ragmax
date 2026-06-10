import { Send, Plus, Settings, Search, Lightbulb, Database } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import styles from './IntegratedInputBox.module.css'
import type { DatasetWithFiles } from '../../types/indexing'

type IntegratedInputBoxProps = {
  onSendMessage: (message: string) => void
  isLoading?: boolean | undefined
  datasets?: DatasetWithFiles[] | undefined
  selectedDataset?: string | undefined
  onDatasetChange?: (datasetId: string) => void
  webSearchEnabled?: boolean | undefined
  onToggleWebSearch?: () => void
  thinkingModeEnabled?: boolean | undefined
  onToggleThinkingMode?: () => void
  debugModeEnabled?: boolean | undefined
  onToggleDebugMode?: () => void
}

export function IntegratedInputBox({
  onSendMessage,
  isLoading = false,
  datasets = [],
  selectedDataset,
  onDatasetChange,
  webSearchEnabled = false,
  onToggleWebSearch,
  thinkingModeEnabled = false,
  onToggleThinkingMode,
  debugModeEnabled = false,
  onToggleDebugMode,
}: IntegratedInputBoxProps) {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const sendDisabled = !message.trim() || isLoading || (Boolean(onDatasetChange) && !selectedDataset)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [message])

  const handleSubmit = () => {
    if (!sendDisabled) {
      onSendMessage(message.trim())
      setMessage('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.inputBox}>
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('retrieval.typeMessage')}
          className={styles.textarea}
          disabled={isLoading}
          rows={1}
        />

        {/* Send Button */}
        <button
          onClick={handleSubmit}
          disabled={sendDisabled}
          className={styles.sendButton}
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </div>

      {/* Toolbar - No separator, integrated at bottom */}
      <div className={styles.toolbar}>
        {/* Left side tools */}
        <div className={styles.toolbarLeft}>
          <button className={styles.toolButton} aria-label="Attach file">
            <Plus size={18} />
          </button>

          {/* Dataset Selector */}
          {datasets.length > 0 && onDatasetChange && (
            <div className={styles.datasetSelector}>
              <Database size={16} className={styles.datasetIcon} />
              <select
                value={selectedDataset || ''}
                onChange={(e) => onDatasetChange(e.target.value)}
                className={styles.datasetSelect}
              >
                <option value="">{t('retrieval.selectDataset')}</option>
                {datasets.map((ds) => (
                  <option key={ds.dataset.dataset_id} value={ds.dataset.dataset_id}>
                    {ds.dataset.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {onToggleWebSearch && (
            <button
              onClick={onToggleWebSearch}
              className={`${styles.toolButton} ${webSearchEnabled ? styles.toolButtonActive : ''}`}
              aria-label={t('retrieval.webSearch')}
              title={t('retrieval.webSearch')}
            >
              <Search size={18} />
            </button>
          )}

          {onToggleThinkingMode && (
            <button
              onClick={onToggleThinkingMode}
              className={`${styles.toolButton} ${thinkingModeEnabled ? styles.toolButtonActive : ''}`}
              aria-label={t('retrieval.thinkingMode')}
              title={t('retrieval.thinkingMode')}
            >
              <Lightbulb size={18} />
            </button>
          )}
        </div>

        {/* Right side tools */}
        <div className={styles.toolbarRight}>
          {onToggleDebugMode && (
            <button
              onClick={onToggleDebugMode}
              className={`${styles.toolButton} ${debugModeEnabled ? styles.toolButtonActive : ''}`}
              aria-label={t('retrieval.toggleDebugMode')}
              title={t('retrieval.toggleDebugMode')}
            >
              <Settings size={18} />
            </button>
          )}

          {/* Model indicator */}
          <div className={styles.modelIndicator}>
            <span className={styles.modelName}>GPT-4</span>
          </div>
        </div>
      </div>
    </div>
  )
}
