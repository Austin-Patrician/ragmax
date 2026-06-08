import { Center, Loader, Text } from '@mantine/core'
import { type ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'
import { ROUTES } from '@/constants/routes'
import { useAuth } from './useAuth'

type RoutePermissionProps = {
  children: ReactNode
  routePath: string
}

export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <Center h="100vh">
        <Loader color="green" />
      </Center>
    )
  }

  if (status === 'unauthenticated') {
    return <Navigate to={ROUTES.login} state={{ from: location }} replace />
  }

  return <Outlet />
}

export function RoutePermission({ children, routePath }: RoutePermissionProps) {
  const { canAccessRoute } = useAuth()

  if (!canAccessRoute(routePath)) {
    return <Navigate to={ROUTES.forbidden} replace />
  }

  return children
}

export function EmptyPermissionState() {
  return (
    <Center h="60vh">
      <Text c="dimmed">No route permissions are assigned to this user.</Text>
    </Center>
  )
}
