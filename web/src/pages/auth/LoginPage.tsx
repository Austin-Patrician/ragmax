import {
  Alert,
  Button,
  Checkbox,
  Group,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { type FormEvent, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/auth/useAuth'
import { ROUTES } from '@/constants/routes'
import classes from './LoginPage.module.css'

type LoginLocationState = {
  from?: {
    pathname?: string
  }
}

export function LoginPage() {
  const { t } = useTranslation()
  const { login, status, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const classNames = {
    screen: classes.screen ?? '',
    backgroundGrid: classes.backgroundGrid ?? '',
    brandBar: classes.brandBar ?? '',
    brandMark: classes.brandMark ?? '',
    brandText: classes.brandText ?? '',
    hero: classes.hero ?? '',
    headline: classes.headline ?? '',
    formTitle: classes.formTitle ?? '',
    panel: classes.panel ?? '',
    form: classes.form ?? '',
    field: classes.field ?? '',
    required: classes.required ?? '',
    row: classes.row ?? '',
    mutedAction: classes.mutedAction ?? '',
    submitButton: classes.submitButton ?? '',
    accountHint: classes.accountHint ?? '',
    adminLink: classes.adminLink ?? '',
    subtitle: classes.subtitle ?? '',
  }

  useEffect(() => {
    if (status === 'authenticated' && user) {
      navigate(resolveRedirect(user.route_permissions, location.state), { replace: true })
    }
  }, [location.state, navigate, status, user])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const loggedInUser = await login({ username, password })
      navigate(resolveRedirect(loggedInUser.route_permissions, location.state), {
        replace: true,
      })
    } catch {
      setError(t('auth.loginFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className={classNames.screen}>
      <div className={classNames.backgroundGrid} aria-hidden="true" />

      <header className={classNames.brandBar}>
        <div className={classNames.brandMark} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <Text className={classNames.brandText}>RAGMax</Text>
      </header>

      <section className={classNames.hero}>
        <Title order={1} className={classNames.headline}>
          {t('auth.heroTitle')}
        </Title>
        <Text className={classNames.subtitle}>{t('auth.loginSubtitle')}</Text>

        <Paper className={classNames.panel} radius="md">
          <form className={classNames.form} onSubmit={handleSubmit}>
            <Stack gap="lg">
              <Title order={2} className={classNames.formTitle}>
                {t('auth.loginTitle')}
              </Title>

              {error ? (
                <Alert color="red" variant="light" title={t('auth.loginErrorTitle')} role="alert">
                  {error}
                </Alert>
              ) : null}

              <TextInput
                className={classNames.field}
                label={
                  <>
                    <span className={classNames.required}>*</span>
                    {t('auth.username')}
                  </>
                }
                placeholder={t('auth.usernamePlaceholder')}
                value={username}
                onChange={(event) => setUsername(event.currentTarget.value)}
                autoComplete="username"
                required
              />
              <PasswordInput
                className={classNames.field}
                label={
                  <>
                    <span className={classNames.required}>*</span>
                    {t('auth.password')}
                  </>
                }
                placeholder={t('auth.passwordPlaceholder')}
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
                autoComplete="current-password"
                required
              />

              <Group className={classNames.row} justify="space-between">
                <Checkbox
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.currentTarget.checked)}
                  label={t('auth.rememberMe')}
                  color="cyan"
                />
                <Text component="span" className={classNames.mutedAction}>
                  {t('auth.forgotPassword')}
                </Text>
              </Group>

              <Button
                type="submit"
                fullWidth
                className={classNames.submitButton}
                loading={submitting}
              >
                {t('auth.login')}
              </Button>

              <Text className={classNames.accountHint}>
                {t('auth.noAccount')}{' '}
                <span className={classNames.adminLink}>{t('auth.contactAdmin')}</span>
              </Text>
            </Stack>
          </form>
        </Paper>
      </section>
    </main>
  )
}

function resolveRedirect(routePermissions: string[], state: unknown): string {
  const locationState = state as LoginLocationState | null
  const requestedPath = locationState?.from?.pathname
  if (
    requestedPath &&
    requestedPath !== ROUTES.login &&
    routePermissions.includes(requestedPath)
  ) {
    return requestedPath
  }

  return routePermissions[0] ?? ROUTES.forbidden
}
