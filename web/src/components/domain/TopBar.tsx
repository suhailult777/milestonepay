import { Moon, Plus, Sun } from 'lucide-react'
import { Button } from '../ui/Button'
import { navigate } from '../../lib/router'
import type { Theme } from '../../lib/useTheme'

export function TopBar({ projectName, theme, onToggleTheme, onAdd }:
  { projectName?: string; theme: Theme; onToggleTheme: () => void; onAdd: () => void }) {
  return (
    <header className="topbar">
      <a className="wordmark" href="/" onClick={e => { e.preventDefault(); navigate('/') }}>MilestonePay</a>
      <span className="topbar-crumb">
        Portfolio{projectName ? <><span aria-hidden="true"> / </span>{projectName}</> : null}
      </span>
      <div className="topbar-actions">
        <Button variant="quiet" className="theme-toggle" onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
        <Button variant="primary" className="add-button" onClick={onAdd} aria-label="Add contract">
          <Plus size={16} /> <span className="add-label">Add contract</span>
        </Button>
      </div>
    </header>
  )
}
