import { User, Bot, ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './ChatMessageArea.module.css'

export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: Array<{
    id: string
    title: string
    score?: number
  }> | undefined
  retrievalSteps?: Array<{
    name: string
    description: string
    duration?: string | undefined
    data?: unknown
  }> | undefined
}

type ChatMessageAreaProps = {
  messages: Message[]
  isLoading?: boolean
  showDebugMode?: boolean
}

function UserMessage({ message }: { message: Message }) {
  return (
    <div className={styles.messageRow}>
      <div className={styles.messageContainer}>
        <div className={styles.userAvatar}>
          <User size={16} />
        </div>
        <div className={styles.messageContent}>
          <div className={styles.messageText}>{message.content}</div>
          <div className={styles.messageTime}>{message.timestamp}</div>
        </div>
      </div>
    </div>
  )
}

function AssistantMessage({
  message,
  showDebugMode,
}: {
  message: Message
  showDebugMode?: boolean
}) {
  const { t } = useTranslation()
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())

  const toggleStep = (index: number) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedSteps(newExpanded)
  }

  return (
    <div className={styles.messageRow}>
      <div className={styles.messageContainer}>
        <div className={styles.assistantAvatar}>
          <Bot size={16} />
        </div>
        <div className={styles.messageContent}>
          <div className={styles.markdownContent}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: (props) => (
                  <a {...props} target="_blank" rel="noreferrer" />
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className={styles.sources}>
              <div className={styles.sourcesTitle}>{t('retrieval.sourcesReferenced')}</div>
              <div className={styles.sourcesList}>
                {message.sources.map((source) => (
                  <div key={source.id} className={styles.sourceItem}>
                    <span className={styles.sourceTitle}>{source.title}</span>
                    {source.score && (
                      <span className={styles.sourceScore}>
                        {(source.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Retrieval Pipeline (Debug Mode) */}
          {showDebugMode && message.retrievalSteps && message.retrievalSteps.length > 0 && (
            <div className={styles.pipeline}>
              <div className={styles.pipelineTitle}>{t('retrieval.retrievalPipeline')}</div>
              <div className={styles.stepsContainer}>
                {message.retrievalSteps.map((step, index) => (
                  <div key={index} className={styles.step}>
                    <div
                      className={styles.stepHeader}
                      onClick={() => toggleStep(index)}
                      role="button"
                      tabIndex={0}
                    >
                      <div className={styles.stepHeaderLeft}>
                        {expandedSteps.has(index) ? (
                          <ChevronDown size={16} />
                        ) : (
                          <ChevronRight size={16} />
                        )}
                        <span className={styles.stepName}>{step.name}</span>
                      </div>
                      {step.duration && (
                        <span className={styles.stepDuration}>{step.duration}</span>
                      )}
                    </div>
                    {expandedSteps.has(index) && (
                      <div className={styles.stepContent}>
                        <p className={styles.stepDescription}>{step.description}</p>
                        {step.data !== undefined && (
                          <pre className={styles.stepData}>
                            {JSON.stringify(step.data, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={styles.messageTime}>{message.timestamp}</div>
        </div>
      </div>
    </div>
  )
}

export function ChatMessageArea({ messages, isLoading, showDebugMode }: ChatMessageAreaProps) {
  const { t } = useTranslation()

  if (messages.length === 0 && !isLoading) {
    return (
      <div className={styles.emptyState}>
        <Bot size={48} className={styles.emptyIcon} />
        <h2 className={styles.emptyTitle}>
          Hi! 👋 {t('retrieval.startConversationHint')}
        </h2>
      </div>
    )
  }

  return (
    <div className={styles.messageArea}>
      {messages.map((message) =>
        message.role === 'user' ? (
          <UserMessage key={message.id} message={message} />
        ) : (
          <AssistantMessage
            key={message.id}
            message={message}
            showDebugMode={showDebugMode ?? false}
          />
        )
      )}

      {isLoading && (
        <div className={styles.messageRow}>
          <div className={styles.messageContainer}>
            <div className={styles.assistantAvatar}>
              <Bot size={16} />
            </div>
            <div className={styles.messageContent}>
              <div className={styles.loadingDots}>
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
