import { Avatar, Text } from '@mantine/core'
import type { Message } from '../../types'
import classes from './Message.module.css'

interface UserMessageProps {
  message: Message
}

export default function UserMessage({ message }: UserMessageProps) {
  const timestamp = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className={classes.userMessageWrapper}>
      <div className={classes.userMessage}>
        <Text size="sm">{message.content}</Text>
        <Text size="xs" className={classes.userTimestamp ?? ''}>
          {timestamp}
        </Text>
      </div>
      <Avatar color="blue" radius="xl" size="sm">
        U
      </Avatar>
    </div>
  )
}
