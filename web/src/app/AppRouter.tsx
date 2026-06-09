import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import {
  EmptyPermissionState,
  ProtectedRoute,
  RoutePermission,
} from '@/auth/ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { ROUTES } from '@/constants/routes'
import { useAuth } from '@/auth/useAuth'
import { ForbiddenPage } from '@/pages/auth/ForbiddenPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import FilesPage from '@/pages/files/FilesPage'
import DatasetsPage from '@/pages/datasets/DatasetsPage'
import CreateDatasetPage from '@/pages/datasets/CreateDatasetPage'
import DatasetDetailPage from '@/pages/datasets/DatasetDetailPage'
import { IndexingPage } from '@/pages/indexing/IndexingPage'
import { RetrievalPage } from '@/pages/retrieval/RetrievalPage'
import { EvaluationOverview } from '@/pages/evaluation/overview/EvaluationOverview'
import { DatasetManagement } from '@/pages/evaluation/datasets/DatasetManagement'
import { ExperimentDetail } from '@/pages/evaluation/experiments/ExperimentDetail'
import { ExperimentComparison } from '@/pages/evaluation/comparison/ExperimentComparison'
import { UserSettingsPage } from '@/pages/user-settings/UserSettingsPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={ROUTES.login} element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<HomeRedirect />} />
            <Route
              path={ROUTES.files}
              element={
                <RoutePermission routePath={ROUTES.files}>
                  <FilesPage />
                </RoutePermission>
              }
            />
            <Route
              path={ROUTES.datasets}
              element={
                <RoutePermission routePath={ROUTES.datasets}>
                  <DatasetsPage />
                </RoutePermission>
              }
            />
            <Route
              path="/datasets/new"
              element={
                <RoutePermission routePath={ROUTES.datasets}>
                  <CreateDatasetPage />
                </RoutePermission>
              }
            />
            <Route
              path="/datasets/:id"
              element={
                <RoutePermission routePath={ROUTES.datasets}>
                  <DatasetDetailPage />
                </RoutePermission>
              }
            />
            <Route
              path={ROUTES.indexing}
              element={
                <RoutePermission routePath={ROUTES.indexing}>
                  <IndexingPage />
                </RoutePermission>
              }
            />
            <Route
              path={ROUTES.retrieval}
              element={
                <RoutePermission routePath={ROUTES.retrieval}>
                  <RetrievalPage />
                </RoutePermission>
              }
            />
            <Route
              path={ROUTES.evaluation}
              element={
                <RoutePermission routePath={ROUTES.evaluation}>
                  <EvaluationOverview />
                </RoutePermission>
              }
            />
            <Route
              path={ROUTES.evaluationDatasets}
              element={
                <RoutePermission routePath={ROUTES.evaluation}>
                  <DatasetManagement />
                </RoutePermission>
              }
            />
            <Route
              path="/evaluation/experiments/:experimentId"
              element={
                <RoutePermission routePath={ROUTES.evaluation}>
                  <ExperimentDetail />
                </RoutePermission>
              }
            />
            <Route
              path="/evaluation/compare"
              element={
                <RoutePermission routePath={ROUTES.evaluation}>
                  <ExperimentComparison />
                </RoutePermission>
              }
            />
            <Route path={ROUTES.userSettings} element={<UserSettingsPage />} />
            <Route path={ROUTES.forbidden} element={<ForbiddenPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

function HomeRedirect() {
  const { user } = useAuth()
  const firstRoute = user?.route_permissions[0]

  if (!firstRoute) {
    return <EmptyPermissionState />
  }

  return <Navigate to={firstRoute} replace />
}
