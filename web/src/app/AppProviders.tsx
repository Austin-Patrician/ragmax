import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'
import { MantineProvider, createTheme } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import '@/i18n'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

const theme = createTheme({
  primaryColor: 'green',
  fontFamily: "'IBM Plex Sans', 'Aptos', 'Segoe UI', sans-serif",
  fontFamilyMonospace: "'IBM Plex Mono', 'Cascadia Mono', Consolas, monospace",
  defaultRadius: 'sm',
  headings: {
    fontFamily: "'IBM Plex Sans', 'Aptos', 'Segoe UI', sans-serif",
    fontWeight: '650',
  },
})

type AppProvidersProps = {
  children: ReactNode
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={theme} defaultColorScheme="light">
        <Notifications position="top-right" />
        {children}
      </MantineProvider>
    </QueryClientProvider>
  )
}
