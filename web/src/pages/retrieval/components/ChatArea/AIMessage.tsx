import { Alert, Avatar, Group, Loader, Paper, Stack, Text } from '@mantine/core'
import { IconBrain, IconSparkles } from '@tabler/icons-react'
import type { Message, RetrievalMode } from '../../types'
import SourceReferences from '../SourceReferences/SourceReferences'
import RetrievalSteps from '../RetrievalSteps/RetrievalSteps'
import classes from './Message.module.css'

interface AIMessageProps {
  message: Message
  mode: RetrievalMode
}

export default function AIMessage({ message, mode }: AIMessageProps) {
  const timestamp = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className={classes.aiMessageWrapper}>
      <Avatar color="violet" radius="xl" size="sm">
        <IconSparkles size={18} />
      </Avatar>

      <Stack gap="md" className={classes.aiMessageStack ?? ''}>
        {/* Dev Mode: Retrieval Steps - 顶部显示 */}
        {mode === 'dev' && message.retrievalSteps && message.retrievalSteps.length > 0 && (
          <Paper
            withBorder
            p="md"
            radius="md"
            className={classes.retrievalStepsContainer ?? ''}
          >
            <RetrievalSteps steps={message.retrievalSteps} />
          </Paper>
        )}

        {/* Thinking Indicator */}
        {message.isThinking && (
          <Alert icon={<IconBrain size={18} />} color="orange" variant="light">
            <Group gap="xs">
              <Loader size="xs" color="orange" />
              <Text size="sm">Thinking...</Text>
            </Group>
          </Alert>
        )}

        {/* AI Response - 中间主体内容 */}
        <Paper radius="md" className={classes.aiMessage ?? ''}>
          <Text size="sm" className={classes.messageContent ?? ''}>
            {message.content}
          </Text>
          <Text size="xs" className={classes.aiTimestamp ?? ''}>
            {timestamp}
          </Text>
        </Paper>

        {/* Sources - 底部折叠区域 */}
        {message.sources && message.sources.length > 0 && (
          <SourceReferences sources={message.sources} />
        )}
      </Stack>
    </div>
  )
}
