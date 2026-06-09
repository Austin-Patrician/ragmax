export type RetrievalMode = 'dev' | 'production'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: SourceReference[]
  retrievalSteps?: RetrievalStep[]
  isThinking?: boolean
}

export interface SourceReference {
  id: string
  filename: string
  pageRange?: string
  relevanceScore: number
  excerpt?: string
}

export interface RetrievalStep {
  type: 'query_understanding' | 'vector_search' | 'rerank' | 'context_assembly'
  title: string
  description: string
  duration: number
  data?: Record<string, unknown>
}

export interface Conversation {
  id: string
  title: string
  lastMessage?: string
  timestamp: string
  messageCount: number
}

export interface ChatRequest {
  conversationId?: string
  datasetId: string
  message: string
  mode: RetrievalMode
  options: {
    webSearchEnabled: boolean
    thinkingMode: boolean
    temperature: number
    topK: number
    model: string
  }
}

export interface ChatResponse {
  messageId: string
  content: string
  sources: SourceReference[]
  retrievalSteps?: RetrievalStep[]
  timestamp: string
}
