import { Plus, Search, MessageSquare, MoreVertical } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import styles from './ConversationSidebar.module.css'

export type Conversation = {
  id: string
  title: string
  lastMessage?: string
  timestamp: string
  dataset?: string
}

type ConversationSidebarProps = {
  conversations: Conversation[]
  currentConversationId?: string | undefined
  onNewConversation: () => void
  onSelectConversation: (id: string) => void
  onDeleteConversation?: (id: string) => void
  isCollapsed?: boolean | undefined
  onToggle?: () => void
}

export function ConversationSidebar({
  conversations,
  currentConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  isCollapsed = false,
}: ConversationSidebarProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (isCollapsed) {
    return (
      <div className={styles.sidebarCollapsed}>
        <button
          onClick={onNewConversation}
          className={styles.collapsedNewButton}
          aria-label={t('retrieval.newConversation')}
        >
          <Plus size={20} />
        </button>
      </div>
    )
  }

  return (
    <div className={styles.sidebar}>
      {/* Header */}
      <div className={styles.header}>
        <button onClick={onNewConversation} className={styles.newButton}>
          <Plus size={18} />
          <span>{t('retrieval.newConversation')}</span>
        </button>
      </div>

      {/* Search */}
      <div className={styles.searchContainer}>
        <Search size={16} className={styles.searchIcon} />
        <input
          type="text"
          placeholder={t('retrieval.conversations')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={styles.searchInput}
        />
      </div>

      {/* Conversation List */}
      <div className={styles.conversationList}>
        {filteredConversations.length === 0 ? (
          <div className={styles.emptyState}>
            <MessageSquare size={40} className={styles.emptyIcon} />
            <p className={styles.emptyTitle}>{t('retrieval.noConversations')}</p>
            <p className={styles.emptyHint}>{t('retrieval.startConversation')}</p>
          </div>
        ) : (
          filteredConversations.map((conv) => (
            <div
              key={conv.id}
              className={`${styles.conversationItem} ${
                currentConversationId === conv.id ? styles.active : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className={styles.conversationContent}>
                <div className={styles.conversationTitle}>{conv.title}</div>
                {conv.lastMessage && (
                  <div className={styles.conversationPreview}>{conv.lastMessage}</div>
                )}
                <div className={styles.conversationMeta}>
                  <span className={styles.timestamp}>{conv.timestamp}</span>
                  {conv.dataset && (
                    <>
                      <span className={styles.metaDivider}>·</span>
                      <span className={styles.dataset}>{conv.dataset}</span>
                    </>
                  )}
                </div>
              </div>
              {onDeleteConversation && (
                <button
                  className={styles.moreButton}
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteConversation(conv.id)
                  }}
                  aria-label="More options"
                >
                  <MoreVertical size={16} />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
