import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Paper,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Tooltip,
} from '@mantine/core'
import {
  IconChevronLeft,
  IconChevronRight,
  IconMessageCircle,
  IconMessagePlus,
  IconSearch,
} from '@tabler/icons-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Conversation } from '../../types'
import classes from './ConversationList.module.css'

interface ConversationListProps {
  conversations: Conversation[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNewConversation: () => void
  collapsed: boolean
  onToggleCollapsed: () => void
}

export default function ConversationList({
  conversations,
  selectedId,
  onSelect,
  onNewConversation,
  collapsed,
  onToggleCollapsed,
}: ConversationListProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )
  const collapseLabel = collapsed ? 'Expand sidebar' : 'Collapse sidebar'

  return (
    <Paper
      component="aside"
      className={`${classes.container} ${collapsed ? classes.collapsed : ''}`}
      aria-label={t('retrieval.conversations')}
    >
      <Stack gap="md" className={classes.stack ?? ''}>
        <div className={classes.header}>
          <Group gap="sm" wrap="nowrap" className={classes.brand ?? ''}>
            <ThemeIcon className={classes.brandIcon ?? ''} variant="filled" size={42}>
              <IconMessageCircle size={20} />
            </ThemeIcon>
            <div className={classes.titleBlock}>
              <Text className={classes.kicker ?? ''}>Retrieval</Text>
              <Text className={classes.title ?? ''} lineClamp={1}>
                {t('retrieval.conversations')}
              </Text>
            </div>
          </Group>
          <Tooltip label={collapseLabel} withArrow>
            <ActionIcon
              className={classes.collapseButton ?? ''}
              variant="subtle"
              aria-label={collapseLabel}
              aria-expanded={!collapsed}
              onClick={onToggleCollapsed}
            >
              {collapsed ? <IconChevronRight size={18} /> : <IconChevronLeft size={18} />}
            </ActionIcon>
          </Tooltip>
        </div>

        <div className={classes.newConversation}>
          {collapsed ? (
            <Tooltip label={t('retrieval.newConversation')} withArrow position="right">
              <ActionIcon
                className={classes.newIconButton ?? ''}
                variant="filled"
                aria-label={t('retrieval.newConversation')}
                onClick={onNewConversation}
              >
                <IconMessagePlus size={19} />
              </ActionIcon>
            </Tooltip>
          ) : (
            <Button
              className={classes.newButton ?? ''}
              leftSection={<IconMessagePlus size={18} />}
              onClick={onNewConversation}
              size="sm"
              fullWidth
            >
              {t('retrieval.newConversation')}
            </Button>
          )}
        </div>

        <div className={classes.searchWrap}>
          <TextInput
            aria-label={t('common.search')}
            placeholder={t('common.search')}
            leftSection={<IconSearch size={16} />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="sm"
            classNames={{ input: classes.searchInput ?? '' }}
          />
        </div>

        <Group className={classes.sectionHeader ?? ''} justify="space-between" wrap="nowrap">
          <Text className={classes.sectionTitle ?? ''}>Sessions</Text>
          <Badge className={classes.countBadge ?? ''} variant="light">
            {filteredConversations.length}
          </Badge>
        </Group>

        <ScrollArea className={classes.scrollArea ?? ''} type="hover">
          <Stack gap="xs" className={classes.list ?? ''}>
            {filteredConversations.length === 0 ? (
              <div className={classes.emptyState}>
                <ThemeIcon className={classes.emptyIcon ?? ''} variant="light" size={38}>
                  <IconMessageCircle size={18} />
                </ThemeIcon>
                <Text className={classes.emptyText ?? ''}>{t('retrieval.noConversations')}</Text>
              </div>
            ) : (
              filteredConversations.map((conv) => {
                const card = (
                  <button
                    type="button"
                    className={`${classes.conversationCard} ${
                      selectedId === conv.id ? classes.selected : ''
                    }`}
                    onClick={() => onSelect(conv.id)}
                    aria-label={conv.title}
                  >
                    <span className={classes.cardIcon} aria-hidden="true">
                      <IconMessageCircle size={16} />
                    </span>
                    <span className={classes.cardBody}>
                      <Text className={classes.cardTitle ?? ''} lineClamp={1}>
                        {conv.title}
                      </Text>
                      {conv.lastMessage && (
                        <Text className={classes.cardPreview ?? ''} lineClamp={2}>
                          {conv.lastMessage}
                        </Text>
                      )}
                      <Text className={classes.cardDate ?? ''}>
                        {new Date(conv.timestamp).toLocaleDateString()}
                      </Text>
                    </span>
                    {conv.messageCount > 0 && (
                      <span className={classes.messageCount}>{conv.messageCount}</span>
                    )}
                  </button>
                )

                return collapsed ? (
                  <Tooltip key={conv.id} label={conv.title} position="right" withArrow>
                    {card}
                  </Tooltip>
                ) : (
                  <div key={conv.id}>{card}</div>
                )
              })
            )}
          </Stack>
        </ScrollArea>
      </Stack>
    </Paper>
  )
}
