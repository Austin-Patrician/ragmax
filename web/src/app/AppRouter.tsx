import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AppLayout } from '@/components/layout/AppLayout'
import { ROUTES } from '@/constants/routes'
import { IndexingPage } from '@/pages/indexing/IndexingPage'
import { RetrievalPage } from '@/pages/retrieval/RetrievalPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to={ROUTES.indexing} replace />} />
          <Route path={ROUTES.indexing} element={<IndexingPage />} />
          <Route path={ROUTES.retrieval} element={<RetrievalPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
