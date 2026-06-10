import { apiBaseUrl, apiClient, assertApiData, authenticatedFetch } from './client'
import type {
  RetrievalAnswerRequest,
  RetrievalAnswerResponse,
  RetrievalSearchRequest,
  RetrievalSearchResponse,
} from '@/types'

export async function searchRetrieval(
  request: RetrievalSearchRequest,
): Promise<RetrievalSearchResponse> {
  const { data, error } = await apiClient.POST('/api/v1/retrieval/search', {
    body: request,
  })
  return assertApiData(data, error)
}

export async function answerRetrieval(
  request: RetrievalAnswerRequest,
): Promise<RetrievalAnswerResponse> {
  let finalResponse: RetrievalAnswerResponse | undefined
  await answerRetrievalStream(request, {
    onDone: (response) => {
      finalResponse = response
    },
  })

  if (!finalResponse) {
    throw new Error('No final answer received.')
  }
  return finalResponse
}

export type RetrievalAnswerStreamHandlers = {
  onStatus?: (data: Record<string, unknown>) => void
  onContexts?: (data: Record<string, unknown>) => void
  onAnswerDelta?: (text: string) => void
  onDone?: (response: RetrievalAnswerResponse) => void
  onError?: (error: Error) => void
}

export async function answerRetrievalStream(
  request: RetrievalAnswerRequest,
  handlers: RetrievalAnswerStreamHandlers = {},
): Promise<void> {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/retrieval/answer`, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const payload = await response.text()
    throw new Error(payload || `Request failed with status ${response.status}`)
  }
  if (!response.body) {
    throw new Error('Streaming response body is empty.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      handleSseBlock(block, handlers)
    }
  }

  buffer += decoder.decode()
  if (buffer.trim()) {
    handleSseBlock(buffer, handlers)
  }
}

function handleSseBlock(block: string, handlers: RetrievalAnswerStreamHandlers) {
  const event = parseSseBlock(block)
  if (!event) {
    return
  }

  if (event.event === 'status') {
    handlers.onStatus?.(event.data)
    return
  }
  if (event.event === 'contexts') {
    handlers.onContexts?.(event.data)
    return
  }
  if (event.event === 'answer_delta') {
    const text = typeof event.data.text === 'string' ? event.data.text : ''
    if (text) {
      handlers.onAnswerDelta?.(text)
    }
    return
  }
  if (event.event === 'done') {
    handlers.onDone?.(event.data as RetrievalAnswerResponse)
    return
  }
  if (event.event === 'error') {
    const message = typeof event.data.message === 'string' ? event.data.message : 'Stream failed.'
    const error = new Error(message)
    handlers.onError?.(error)
    throw error
  }
}

function parseSseBlock(block: string): { event: string; data: Record<string, unknown> } | null {
  let event = 'message'
  const dataLines: string[] = []

  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart())
    }
  }

  if (dataLines.length === 0) {
    return null
  }

  return {
    event,
    data: JSON.parse(dataLines.join('\n')) as Record<string, unknown>,
  }
}
