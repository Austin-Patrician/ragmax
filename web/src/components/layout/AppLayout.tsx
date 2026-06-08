import { ActionIcon, Avatar, Burger, Group, Text } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { CircleHelp, LogOut, Sparkles, Sun, Workflow } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink as RouterNavLink, Outlet, useNavigate } from 'react-router'
import { useAuth } from '@/auth/useAuth'
import { APP_NAME } from '@/constants/app'
import { NAV_ITEMS } from '@/constants/navigation'
import { ROUTES } from '@/constants/routes'
import { LanguageSwitcher } from './LanguageSwitcher'
import classes from './AppLayout.module.css'

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure(false)
  const { t } = useTranslation()
  const { canAccessRoute, logout, user } = useAuth()
  const navigate = useNavigate()
  const allowedNavItems = NAV_ITEMS.filter((item) => canAccessRoute(item.to))
  const userInitial = user?.username?.slice(0, 1).toUpperCase() ?? 'U'
  const classNames = {
    shell: classes.shell ?? '',
    skipLink: classes.skipLink ?? '',
    header: classes.header ?? '',
    brand: classes.brand ?? '',
    brandMark: classes.brandMark ?? '',
    brandText: classes.brandText ?? '',
    upgrade: classes.upgrade ?? '',
    navWrap: classes.navWrap ?? '',
    navWrapOpen: classes.navWrapOpen ?? '',
    navRail: classes.navRail ?? '',
    navItem: classes.navItem ?? '',
    navItemActive: classes.navItemActive ?? '',
    utilityBar: classes.utilityBar ?? '',
    utilityIcon: classes.utilityIcon ?? '',
    languageSlot: classes.languageSlot ?? '',
    userName: classes.userName ?? '',
    avatar: classes.avatar ?? '',
    main: classes.main ?? '',
  }

  async function handleLogout() {
    await logout()
    navigate(ROUTES.login, { replace: true })
  }

  return (
    <div className={classNames.shell}>
      <a className={classNames.skipLink} href="#main-content">
        {t('app.skipToMain')}
      </a>

      <header className={classNames.header}>
        <Group className={classNames.brand} gap="sm">
          <div className={classNames.brandMark} aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
          <Text className={classNames.brandText}>{t('app.brandName', APP_NAME)}</Text>
          <span className={classNames.upgrade}>
            <Sparkles size={13} />
            {t('app.upgrade')}
          </span>
        </Group>

        <nav
          className={`${classNames.navWrap} ${opened ? classNames.navWrapOpen : ''}`}
          aria-label={t('nav.primary')}
        >
          <div className={classNames.navRail}>
            {allowedNavItems.map((item) => (
              <RouterNavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `${classNames.navItem} ${isActive ? classNames.navItemActive : ''}`
                }
                onClick={close}
              >
                <item.icon size={18} strokeWidth={2} />
                <span>{t(item.labelKey)}</span>
              </RouterNavLink>
            ))}
          </div>
        </nav>

        <Group className={classNames.utilityBar} gap="xs">
          <ActionIcon
            className={classNames.utilityIcon}
            component="a"
            href="https://github.com/Austin-Patrician/ragmax"
            rel="noreferrer"
            target="_blank"
            variant="subtle"
            aria-label={t('app.github')}
          >
            <Workflow size={17} />
          </ActionIcon>
          <ActionIcon
            className={classNames.utilityIcon}
            component="a"
            href="https://github.com/Austin-Patrician/ragmax#readme"
            rel="noreferrer"
            target="_blank"
            variant="subtle"
            aria-label={t('app.help')}
          >
            <CircleHelp size={17} />
          </ActionIcon>
          <div className={classNames.languageSlot}>
            <LanguageSwitcher />
          </div>
          <ActionIcon
            className={classNames.utilityIcon}
            variant="subtle"
            aria-label={t('app.theme')}
            disabled
          >
            <Sun size={17} />
          </ActionIcon>
          <ActionIcon
            className={classNames.utilityIcon}
            variant="subtle"
            aria-label={t('auth.logout')}
            onClick={handleLogout}
          >
            <LogOut size={17} />
          </ActionIcon>
          <Group gap={8} wrap="nowrap">
            <Text className={classNames.userName}>{user?.username}</Text>
            <Avatar className={classNames.avatar} radius="xl" size={40}>
              {userInitial}
            </Avatar>
          </Group>
        </Group>

        <Burger
          opened={opened}
          onClick={toggle}
          hiddenFrom="md"
          aria-label={t('nav.toggle')}
        />
      </header>

      <main id="main-content" className={classNames.main}>
        <Outlet />
      </main>
    </div>
  )
}
