import { Select } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import type { SupportedLanguage } from '@/types'

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()

  return (
    <Select
      aria-label={t('language.label')}
      data={[
        { value: 'en', label: t('language.english') },
        { value: 'zh-CN', label: t('language.chinese') },
      ]}
      value={i18n.language}
      onChange={(value) => {
        if (value) {
          void i18n.changeLanguage(value as SupportedLanguage)
        }
      }}
      size="xs"
      w={132}
      allowDeselect={false}
    />
  )
}
