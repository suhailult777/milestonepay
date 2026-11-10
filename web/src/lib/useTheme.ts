import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(() => {
    const forced = new URLSearchParams(window.location.search).get('theme')
    if (forced === 'light' || forced === 'dark') return forced
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('mp-theme', theme)
  }, [theme])
  return { theme, toggle: () => setTheme(current => current === 'dark' ? 'light' : 'dark') }
}
