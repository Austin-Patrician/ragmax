import type { SupportedLanguage } from '@/types'

const SUPPORTED_LANGUAGES: SupportedLanguage[] = ['en', 'zh-CN']

export function resolveInitialLanguage(language = navigator.language): SupportedLanguage {
  if (SUPPORTED_LANGUAGES.includes(language as SupportedLanguage)) {
    return language as SupportedLanguage
  }

  if (language.toLowerCase().startsWith('zh')) {
    return 'zh-CN'
  }

  return 'en'
}
