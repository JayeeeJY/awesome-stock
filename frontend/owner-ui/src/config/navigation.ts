export type PrimaryNavigationKey = 'cockpit' | 'portfolio' | 'research' | 'plan' | 'review' | 'academy'

export type PrimaryNavigationItem = {
  key: PrimaryNavigationKey
  to: string
  matchPrefixes: string[]
}

export const primaryNavigation: PrimaryNavigationItem[] = [
  { key: 'cockpit', to: '/cockpit', matchPrefixes: ['/cockpit', '/today'] },
  { key: 'portfolio', to: '/portfolio', matchPrefixes: ['/portfolio'] },
  { key: 'research', to: '/research', matchPrefixes: ['/research', '/stocks/', '/decisions'] },
  { key: 'plan', to: '/plan', matchPrefixes: ['/plan'] },
  { key: 'review', to: '/review', matchPrefixes: ['/review', '/evolve'] },
  { key: 'academy', to: '/academy', matchPrefixes: ['/academy', '/learn', '/education'] },
]

export const routeMatchesPrefix = (path: string, prefix: string): boolean =>
  path === prefix || path.startsWith(prefix.endsWith('/') ? prefix : `${prefix}/`)

export const primaryRouteForPath = (path: string): string => {
  const match = primaryNavigation.find(item =>
    item.matchPrefixes.some(prefix => routeMatchesPrefix(path, prefix))
  )
  return match?.to || path
}
