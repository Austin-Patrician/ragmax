import { ActionIcon, Avatar, Burger, Group, Text, UnstyledButton } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { CircleHelp } from 'lucide-react'
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
  const { canAccessRoute, user } = useAuth()
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
    userChip: classes.userChip ?? '',
    userName: classes.userName ?? '',
    avatar: classes.avatar ?? '',
    main: classes.main ?? '',
  }

  return (
    <div className={classNames.shell}>
      <a className={classNames.skipLink} href="#main-content">
        {t('app.skipToMain')}
      </a>

      <header className={classNames.header}>
        <Group className={classNames.brand} gap="sm">
          <div style={{ display: 'flex', alignItems: 'center' }} aria-hidden="true">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="brand-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#4c8df8" />
                  <stop offset="1" stopColor="#55c7c8" />
                </linearGradient>
                <linearGradient id="brand-grad2" x1="22" y1="2" x2="2" y2="22" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#64c9db" />
                  <stop offset="1" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
              <path
                d="M12 2L2 7L12 12L22 7L12 2Z"
                fill="url(#brand-grad)"
              />
              <path
                d="M2 17L12 22L22 17"
                stroke="url(#brand-grad2)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 12L12 17L22 12"
                stroke="url(#brand-grad)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <Text className={classNames.brandText}>{t('app.brandName', APP_NAME)}</Text>
          {/* <span className={classNames.upgrade}>
            <Sparkles size={13} />
            {t('app.upgrade')}
          </span> */}
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
                <item.icon size={16} strokeWidth={2} />
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
            <img src="/github.svg" alt="GitHub" width={18} height={18} style={{ display: 'block' }} />
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
          {/* <ActionIcon
            className={classNames.utilityIcon}
            variant="subtle"
            aria-label={t('app.theme')}
            disabled
          >
            <Sun size={17} />
          </ActionIcon> */}

          <UnstyledButton
            className={classNames.userChip}
            aria-label={t('settings.openUserSettings', 'Open user settings')}
            onClick={() => navigate(ROUTES.userSettings)}
          >
            <Avatar 
              className={classNames.avatar} 
              radius="xl" 
              size={36} 
              variant="gradient" 
              gradient={{ from: 'violet', to: 'cyan', deg: 135 }}
            >
              {userInitial}
            </Avatar>
          </UnstyledButton>
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
