import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Menu } from 'lucide-react'
import styles from './RetrievalPage.module.css'
import { ConversationSidebar, type Conversation } from '@/components/retrieval/ConversationSidebar'
import { ChatMessageArea, type Message } from '@/components/retrieval/ChatMessageArea'
import { IntegratedInputBox } from '@/components/retrieval/IntegratedInputBox'
import { useDatasets } from '@/hooks/useIndexing'
import { answerRetrievalStream } from '@/api/retrieval'
import type { Dataset, RetrievalAnswerRequest, RetrievalAnswerResponse } from '@/types'

export function RetrievalPage() {
  const { t } = useTranslation()
  const { data: datasetsRaw } = useDatasets()

  // State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>()
  const [selectedDataset, setSelectedDataset] = useState<string>()
  const [webSearchEnabled, setWebSearchEnabled] = useState(false)
  const [thinkingModeEnabled, setThinkingModeEnabled] = useState(false)
  const [debugModeEnabled, setDebugModeEnabled] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  // Mock conversations - TODO: Replace with real API
  const [conversations, setConversations] = useState<Conversation[]>([
    {
      id: '1',
      title: '初次问候对话',
      lastMessage: 'Hi! How can I help you today?',
      timestamp: '2小时前',
      dataset: 'Technical Docs',
    },
  ])

  // Mock messages - TODO: Replace with real API
  const [messages, setMessages] = useState<Message[]>([])

  // Convert raw datasets to DatasetWithFiles format
  const datasets =
    datasetsRaw?.map((ds: Dataset) => ({
      dataset: ds,
      files: [],
      file_count: 0,
    })) || []

  const currentConversation = conversations.find((c) => c.id === currentConversationId)

  const handleNewConversation = () => {
    const newId = `${Date.now()}`
    const newConv: Conversation = {
      id: newId,
      title: t('retrieval.newConversation'),
      timestamp: '刚刚',
    }
    setConversations([newConv, ...conversations])
    setCurrentConversationId(newId)
    setMessages([])
  }

  const handleSelectConversation = (id: string) => {
    setCurrentConversationId(id)
    // TODO: Load messages for this conversation from API
    // For now, just clear messages
    setMessages([])
  }

  const handleDeleteConversation = (id: string) => {
    setConversations(conversations.filter((c) => c.id !== id))
    if (currentConversationId === id) {
      setCurrentConversationId(undefined)
      setMessages([])
    }
  }

  const handleSendMessage = async (content: string) => {
    if (!currentConversationId) {
      handleNewConversation()
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      // Build request
      const request: RetrievalAnswerRequest = {
        query: content,
        dataset_id: selectedDataset || '',
        retrieval_top_k: 10,
        rerank_top_k: 5,
      }

      const assistantId = `msg-${Date.now() + 1}`
      const assistantTimestamp = new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      })
      let streamedAnswer = ''

      const upsertAssistantMessage = (patch: Partial<Message>) => {
        setMessages((prev) => {
          const existing = prev.find((message) => message.id === assistantId)
          if (!existing) {
            return [
              ...prev,
              {
                id: assistantId,
                role: 'assistant',
                content: '',
                timestamp: assistantTimestamp,
                ...patch,
              },
            ]
          }

          return prev.map((message) =>
            message.id === assistantId ? { ...message, ...patch } : message
          )
        })
      }

      const statusTextByStage: Record<string, string> = {
        accepted: '正在准备...',
        searching: '正在检索知识库...',
        reranking: '正在重排相关内容...',
        generating: '正在生成答案...',
      }

      await answerRetrievalStream(request, {
        onStatus: (data) => {
          const stage = typeof data.stage === 'string' ? data.stage : ''
          if (!streamedAnswer) {
            upsertAssistantMessage({
              content: statusTextByStage[stage] ?? '正在处理...',
            })
          }
        },
        onAnswerDelta: (text) => {
          streamedAnswer += text
          setIsLoading(false)
          upsertAssistantMessage({ content: streamedAnswer })
        },
        onDone: (response) => {
          setIsLoading(false)
          upsertAssistantMessage({
            content: response.answer || streamedAnswer,
            sources: buildSources(response),
            retrievalSteps: buildRetrievalSteps(response, request, debugModeEnabled),
          })
        },
      })

      // Update conversation last message
      setConversations((prev) =>
        prev.map((c) =>
          c.id === currentConversationId
            ? { ...c, lastMessage: content.slice(0, 50) + '...', timestamp: '刚刚' }
            : c
        )
      )
    } catch (error) {
      console.error('Failed to get answer:', error)
      const errorContent = t('retrieval.error.failedToGetAnswer')
      setMessages((prev) => {
        const lastAssistant = [...prev].reverse().find((message) => message.role === 'assistant')
        if (lastAssistant && !lastAssistant.sources?.length) {
          return prev.map((message) =>
            message.id === lastAssistant.id ? { ...message, content: errorContent } : message
          )
        }
        return [
          ...prev,
          {
            id: `msg-${Date.now() + 1}`,
            role: 'assistant',
            content: errorContent,
            timestamp: new Date().toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            }),
          },
        ]
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      {/* Sidebar */}
      {!isSidebarCollapsed && (
        <ConversationSidebar
          conversations={conversations}
          currentConversationId={currentConversationId}
          onNewConversation={handleNewConversation}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          isCollapsed={isSidebarCollapsed}
          onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />
      )}

      {/* Main Chat Area */}
      <div className={styles.chatContainer}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <button
              className={styles.menuButton}
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              aria-label="Toggle sidebar"
            >
              <Menu size={20} />
            </button>
            <h1 className={styles.conversationTitle}>
              {currentConversation?.title || t('retrieval.title')}
            </h1>
          </div>
          <div className={styles.headerRight}>{/* Add additional header actions if needed */}</div>
        </div>

        {/* Messages */}
        <ChatMessageArea
          messages={messages}
          isLoading={isLoading}
          showDebugMode={debugModeEnabled}
        />

        {/* Input Area */}
        <div className={styles.inputContainer}>
          <div className={styles.inputWrapper}>
            <IntegratedInputBox
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              datasets={datasets}
              selectedDataset={selectedDataset}
              onDatasetChange={setSelectedDataset}
              webSearchEnabled={webSearchEnabled}
              onToggleWebSearch={() => setWebSearchEnabled(!webSearchEnabled)}
              thinkingModeEnabled={thinkingModeEnabled}
              onToggleThinkingMode={() => setThinkingModeEnabled(!thinkingModeEnabled)}
              debugModeEnabled={debugModeEnabled}
              onToggleDebugMode={() => setDebugModeEnabled(!debugModeEnabled)}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function buildRetrievalSteps(
  response: RetrievalAnswerResponse,
  request: RetrievalAnswerRequest,
  enabled: boolean,
): Message['retrievalSteps'] {
  if (!enabled) {
    return undefined
  }

  return [
    {
      name: '检索',
      description: '从知识库中召回相关片段',
      data: {
        count: response.retrieval_count,
        top_k: request.retrieval_top_k,
      } as unknown,
    },
    {
      name: '重排',
      description: '对召回结果进行相关性重排',
      data: {
        count: response.rerank_count,
        reranker: response.reranker,
      } as unknown,
    },
    {
      name: '生成',
      description: '基于上下文生成最终答案',
      data: {
        generator: response.answer_generator,
        usage: response.metadata?.usage,
      } as unknown,
    },
  ]
}

function buildSources(response: RetrievalAnswerResponse): Message['sources'] {
  return response.citations.map((citation) => ({
    id: citation.citation_id,
    title: citation.filename || citation.node_id,
    score: response.contexts.find((ctx) => ctx.citation_id === citation.citation_id)?.score || 0,
  }))
}
