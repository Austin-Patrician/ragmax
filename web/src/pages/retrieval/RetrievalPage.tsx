import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Menu } from 'lucide-react'
import styles from './RetrievalPage.module.css'
import { ConversationSidebar, type Conversation } from '@/components/retrieval/ConversationSidebar'
import { ChatMessageArea, type Message } from '@/components/retrieval/ChatMessageArea'
import { IntegratedInputBox } from '@/components/retrieval/IntegratedInputBox'
import { useDatasets } from '@/hooks/useIndexing'

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
    datasetsRaw?.map((ds: any) => ({
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

    // TODO: Replace with real API call
    setTimeout(() => {
      const retrievalSteps: Array<{
        name: string
        description: string
        duration?: string | undefined
        data?: unknown
      }> | undefined = debugModeEnabled
        ? [
            {
              name: '查询理解',
              description: '分析用户问题，提取关键词和意图',
              duration: '45ms',
              data: { query: content, keywords: ['示例', '关键词'] } as unknown,
            },
            {
              name: '向量检索',
              description: '在向量数据库中搜索相关文档',
              duration: '120ms',
              data: { topK: 10, results: 3 } as unknown,
            },
            {
              name: '重排序',
              description: '使用 Reranker 模型对结果重新排序',
              duration: '230ms',
              data: { model: 'bge-reranker-v2-m3' } as unknown,
            },
            {
              name: '上下文组装',
              description: '将检索结果组装成上下文',
              duration: '15ms',
              data: { contextLength: 2048 } as unknown,
            },
          ]
        : undefined

      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content:
          '这是一个模拟回复。实际实现中，这里会调用后端 API 进行检索和生成答案。\n\n根据您的问题，我可以提供以下信息...',
        timestamp: new Date().toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit',
        }),
        sources: [
          { id: '1', title: 'Document A.pdf', score: 0.95 },
          { id: '2', title: 'Document B.pdf', score: 0.87 },
          { id: '3', title: 'Document C.pdf', score: 0.82 },
        ],
        retrievalSteps: retrievalSteps,
      }
      setMessages((prev) => [...prev, assistantMessage])
      setIsLoading(false)

      // Update conversation last message
      setConversations((prev) =>
        prev.map((c) =>
          c.id === currentConversationId
            ? { ...c, lastMessage: content.slice(0, 50) + '...', timestamp: '刚刚' }
            : c
        )
      )
    }, 1500)
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
