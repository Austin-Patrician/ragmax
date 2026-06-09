import { Badge, Group, ScrollArea, Stack, Text, ThemeIcon } from '@mantine/core'
import { IconSparkles } from '@tabler/icons-react'
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { Message, RetrievalMode } from '../../types'
import AIMessage from './AIMessage'
import UserMessage from './UserMessage'
import classes from './ChatArea.module.css'

interface ChatAreaProps {
  messages: Message[]
  mode: RetrievalMode
}

export default function ChatArea({ messages, mode }: ChatAreaProps) {
  const { t } = useTranslation()
  const viewport = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive.
  useEffect(() => {
    if (viewport.current) {
      viewport.current.scrollTo({
        top: viewport.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages])

  return (
    <section className={classes.chatShell} aria-label="Conversation">
      <div className={classes.header}>
        <Group gap="sm" wrap="nowrap" className={classes.headerTitle ?? ''}>
          <ThemeIcon className={classes.headerIcon ?? ''} variant="light" size={40}>
            <IconSparkles size={19} />
          </ThemeIcon>
          <div className={classes.headerText}>
            <Text className={classes.title ?? ''}>Conversation</Text>
            <Text className={classes.subtitle ?? ''}>
              {messages.length === 1 ? '1 message' : `${messages.length} messages`}
            </Text>
          </div>
        </Group>
        <Badge
          className={(mode === 'dev' ? classes.devBadge : classes.modeBadge) ?? ''}
          variant="light"
        >
          {mode === 'dev' ? 'Dev' : 'Prod'}
        </Badge>
      </div>

      <ScrollArea className={classes.scrollArea ?? ''} viewportRef={viewport} type="hover">
        <div className={classes.container}>
          {messages.length === 0 ? (
            <div className={classes.emptyState}>
              <ThemeIcon className={classes.emptyIcon ?? ''} variant="light" size={54}>
                <IconSparkles size={24} />
              </ThemeIcon>
              <Text className={classes.emptyTitle ?? ''}>{t('retrieval.startConversation')}</Text>
              <Text className={classes.emptyHint ?? ''}>{t('retrieval.startConversationHint')}</Text>
            </div>
          ) : (
            <Stack gap="lg" className={classes.messageList ?? ''}>
              {messages.map((message) =>
                message.role === 'user' ? (
                  <UserMessage key={message.id} message={message} />
                ) : (
                  <AIMessage key={message.id} message={message} mode={mode} />
                )
              )}
            </Stack>
          )}
        </div>
      </ScrollArea>
    </section>
  )
}
