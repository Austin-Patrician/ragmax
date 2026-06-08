import { Group, Paper, Text, Title } from '@mantine/core'
import { type ReactNode } from 'react'

type DataPanelProps = {
  title: string
  description?: string
  action?: ReactNode
  children: ReactNode
}

export function DataPanel({ title, description, action, children }: DataPanelProps) {
  return (
    <Paper withBorder p="lg" radius="sm">
      <Group justify="space-between" align="start" mb="md" gap="md">
        <div>
          <Title order={3} size="h4">
            {title}
          </Title>
          {description ? (
            <Text size="sm" c="dimmed" mt={4}>
              {description}
            </Text>
          ) : null}
        </div>
        {action}
      </Group>
      {children}
    </Paper>
  )
}
