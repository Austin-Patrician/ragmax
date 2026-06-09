import { BarChart3, Blocks, Database, FileText, Search } from 'lucide-react'
import { ROUTES } from './routes'

export const NAV_ITEMS = [
  { to: ROUTES.files, labelKey: 'nav.files', icon: FileText },
  { to: ROUTES.datasets, labelKey: 'nav.datasets', icon: Database },
  { to: ROUTES.indexing, labelKey: 'nav.indexing', icon: Blocks },
  { to: ROUTES.retrieval, labelKey: 'nav.retrieval', icon: Search },
  { to: ROUTES.evaluation, labelKey: 'nav.evaluation', icon: BarChart3 },
] as const
