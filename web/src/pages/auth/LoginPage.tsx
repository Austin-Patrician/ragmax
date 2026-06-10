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
import { APP_NAME } from '@/constants/app'
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
    blobTopLeft: classes.blobTopLeft ?? '',
    blobBottomRight: classes.blobBottomRight ?? '',
    gridPattern: classes.gridPattern ?? '',
    container: classes.container ?? '',
    header: classes.header ?? '',
    logoWrapper: classes.logoWrapper ?? '',
    title: classes.title ?? '',
    subtitle: classes.subtitle ?? '',
    panel: classes.panel ?? '',
    form: classes.form ?? '',
    field: classes.field ?? '',
    required: classes.required ?? '',
    row: classes.row ?? '',
    mutedAction: classes.mutedAction ?? '',
    submitButton: classes.submitButton ?? '',
    accountHint: classes.accountHint ?? '',
    adminLink: classes.adminLink ?? '',
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
      setError(t('auth.loginFailed', 'Invalid credentials'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className={classNames.screen}>
      <div className={classNames.blobTopLeft} />
      <div className={classNames.blobBottomRight} />
      <div className={classNames.gridPattern} />

      <div className={classNames.container}>
        <header className={classNames.header}>
          <div className={classNames.logoWrapper}>
            <svg
              width="56"
              height="56"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="login-grad1" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#4c8df8" />
                  <stop offset="1" stopColor="#55c7c8" />
                </linearGradient>
                <linearGradient id="login-grad2" x1="22" y1="2" x2="2" y2="22" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#64c9db" />
                  <stop offset="1" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
              <path
                d="M12 2L2 7L12 12L22 7L12 2Z"
                fill="url(#login-grad1)"
              />
              <path
                d="M2 17L12 22L22 17"
                stroke="url(#login-grad2)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 12L12 17L22 12"
                stroke="url(#login-grad1)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <Title order={1} className={classNames.title}>
            {t('app.brandName', APP_NAME)}
          </Title>
          <Text className={classNames.subtitle}>
            {t('auth.loginSubtitle', 'Empower your intelligence with connected data.')}
          </Text>
        </header>

        <Paper className={classNames.panel} radius="xl" p="xl" withBorder={false}>
          <form className={classNames.form} onSubmit={handleSubmit}>
            <Stack gap="lg">
              {error ? (
                <Alert color="red" variant="light" title={t('auth.loginErrorTitle', 'Error')} role="alert">
                  {error}
                </Alert>
              ) : null}

              <TextInput
                className={classNames.field}
                label={
                  <>
                    <span className={classNames.required}>*</span>
                    {t('auth.username', 'Username')}
                  </>
                }
                placeholder={t('auth.usernamePlaceholder', 'Enter your username')}
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
                    {t('auth.password', 'Password')}
                  </>
                }
                placeholder={t('auth.passwordPlaceholder', 'Enter your password')}
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
                autoComplete="current-password"
                required
              />

              <Group className={classNames.row} justify="space-between">
                <Checkbox
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.currentTarget.checked)}
                  label={t('auth.rememberMe', 'Remember me')}
                  color="cyan"
                  styles={{
                    label: { color: '#6b7280', fontWeight: 600, fontSize: '14px', cursor: 'pointer' },
                    input: { cursor: 'pointer' }
                  }}
                />
                <Text component="span" className={classNames.mutedAction}>
                  {t('auth.forgotPassword', 'Forgot password?')}
                </Text>
              </Group>

              <Button
                type="submit"
                fullWidth
                className={classNames.submitButton}
                loading={submitting}
              >
                {t('auth.login', 'Sign in to workspace')}
              </Button>

              <Text className={classNames.accountHint}>
                {t('auth.noAccount', 'Need an account? ')}
                <span className={classNames.adminLink}>{t('auth.contactAdmin', 'Contact admin')}</span>
              </Text>
            </Stack>
          </form>
        </Paper>
      </div>
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
