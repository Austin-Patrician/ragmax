import { BarChart3, Blocks, Search } from 'lucide-react'
import { ROUTES } from './routes'

export const NAV_ITEMS = [
  { to: ROUTES.indexing, labelKey: 'nav.indexing', icon: Blocks },
  { to: ROUTES.retrieval, labelKey: 'nav.retrieval', icon: Search },
  { to: ROUTES.evaluation, labelKey: 'nav.evaluation', icon: BarChart3 },
] as const
