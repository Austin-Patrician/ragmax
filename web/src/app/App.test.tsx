import { render, screen } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import { App } from './App'

afterEach(() => {
  vi.unstubAllGlobals()
})

test('renders the Ragmax console shell for an authenticated user', async () => {
  vi.stubGlobal('fetch', vi.fn(mockFetch))

  render(<App />)

  expect(await screen.findByText('RAGMax')).toBeInTheDocument()
  expect(screen.getByText('Indexing')).toBeInTheDocument()
  expect(screen.getByText('Retrieval')).toBeInTheDocument()
  expect(screen.getByText('Evaluation')).toBeInTheDocument()
})

async function mockFetch(input: RequestInfo | URL): Promise<Response> {
  const url = input instanceof Request ? input.url : input.toString()
  if (url.endsWith('/api/v1/auth/refresh')) {
    return jsonResponse({
      access_token: 'test-access-token',
      token_type: 'bearer',
      expires_in: 900,
      user: {
        user_id: 'user_test',
        username: 'test-user',
        route_permissions: ['/indexing', '/retrieval', '/evaluation'],
      },
    })
  }
  if (
    url.endsWith('/api/v1/indexing/profiles') ||
    url.endsWith('/api/v1/indexing/parsers')
  ) {
    return jsonResponse([])
  }
  return jsonResponse({ detail: 'not found' }, { status: 404 })
}

function jsonResponse(payload: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(payload), {
    status: init?.status ?? 200,
    headers: { 'Content-Type': 'application/json' },
  })
}
