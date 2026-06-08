import { AppShell, Burger, Group, NavLink, Text, Title } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { Server } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink as RouterNavLink, Outlet } from 'react-router'
import { API_VERSION_LABEL, APP_NAME } from '@/constants/app'
import { NAV_ITEMS } from '@/constants/navigation'
import { LanguageSwitcher } from './LanguageSwitcher'
import classes from './AppLayout.module.css'

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure()
  const { t } = useTranslation()
  const classNames = {
    shell: classes.shell ?? '',
    header: classes.header ?? '',
    mark: classes.mark ?? '',
    title: classes.title ?? '',
    navbar: classes.navbar ?? '',
    navItem: classes.navItem ?? '',
    main: classes.main ?? '',
  }

  return (
    <AppShell
      header={{ height: 64 }}
      navbar={{
        width: 244,
        breakpoint: 'sm',
        collapsed: { mobile: !opened },
      }}
      padding="lg"
      className={classNames.shell}
    >
      <AppShell.Header className={classNames.header}>
        <Group h="100%" px="lg" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <div className={classNames.mark}>
              <Server size={18} />
            </div>
            <div>
              <Title order={3} className={classNames.title}>
                {t('app.name', APP_NAME)}
              </Title>
              <Text size="xs" c="dimmed">
                {t('app.apiLabel', API_VERSION_LABEL)}
              </Text>
            </div>
          </Group>
          <LanguageSwitcher />
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md" className={classNames.navbar}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            component={RouterNavLink}
            to={item.to}
            label={t(item.labelKey)}
            leftSection={<item.icon size={18} />}
            className={classNames.navItem}
            onClick={close}
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main className={classNames.main}>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  )
}
