import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'
import { resolveInitialLanguage } from '@/utils/language'
import { en } from './resources/en'
import { zhCN } from './resources/zh-CN'

void i18next.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    'zh-CN': { translation: zhCN },
  },
  lng: resolveInitialLanguage(),
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
})

export { i18next }
