import { Badge } from '@mantine/core'

type StatusBadgeProps = {
  value: string | null | undefined
}

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = value ?? 'unknown'
  const color =
    normalized === 'succeeded'
      ? 'green'
      : normalized === 'failed'
        ? 'red'
        : normalized === 'skipped'
          ? 'gray'
          : 'yellow'

  return (
    <Badge color={color} variant="light" tt="none">
      {normalized}
    </Badge>
  )
}
