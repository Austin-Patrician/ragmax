import { render, screen } from '@testing-library/react'
import { App } from './App'

test('renders the Ragmax console shell', () => {
  render(<App />)

  expect(screen.getByText('Ragmax Console')).toBeInTheDocument()
  expect(screen.getByText('Indexing')).toBeInTheDocument()
  expect(screen.getByText('Retrieval')).toBeInTheDocument()
})
