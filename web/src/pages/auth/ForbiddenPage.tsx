import { Button, Group, Paper, Stack, Text, Title } from '@mantine/core'
import { ShieldAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { useAuth } from '@/auth/useAuth'
import { ROUTES } from '@/constants/routes'

export function ForbiddenPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const fallbackRoute = user?.route_permissions[0] ?? ROUTES.login

  return (
    <Paper p="xl" radius={0} withBorder>
      <Stack gap="lg">
        <Group gap="md" align="flex-start">
          <ShieldAlert color="var(--ragmax-warning)" size={34} />
          <div>
            <Title order={1}>{t('auth.forbiddenTitle')}</Title>
            <Text c="dimmed" mt={4}>
              {t('auth.forbiddenDescription')}
            </Text>
          </div>
        </Group>
        <Button color="green" onClick={() => navigate(fallbackRoute, { replace: true })}>
          {t('auth.backToAllowedRoute')}
        </Button>
      </Stack>
    </Paper>
  )
}
