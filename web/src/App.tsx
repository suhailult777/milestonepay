import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api/client'
import { DemoBanner } from './components/domain/DemoBanner'
import { TopBar } from './components/domain/TopBar'
import { Dialog } from './components/ui/Dialog'
import { ToastStack, type Toast } from './components/ui/Toast'
import { OverviewPage } from './features/overview/OverviewPage'
import { WorkbenchPage } from './features/workbench/WorkbenchPage'
import { NewContractPage } from './features/new-contract/NewContractPage'
import KitPage from './features/kit/KitPage'
import { navigate, usePath } from './lib/router'
import { useTheme } from './lib/useTheme'
import type { Info, PortfolioBrief, Project, ProjectSummary } from './types'

export default function App() {
  if (window.location.pathname === '/kit') return <KitPage />
  return <Shell />
}

function Shell() {
  const path = usePath()
  const { theme, toggle } = useTheme()
  const [info, setInfo] = useState<Info | null>(null)
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [details, setDetails] = useState<Project[]>([])
  const [brief, setBrief] = useState<PortfolioBrief | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toasts, setToasts] = useState<Toast[]>([])
  const [resetOpen, setResetOpen] = useState(false)
  const toastId = useRef(0)
  const loadingRef = useRef(false)

  const notify = (kind: 'ok' | 'err', text: string) => {
    const id = ++toastId.current
    setToasts(all => [...all, { id, kind, text }])
    window.setTimeout(() => setToasts(all => all.filter(t => t.id !== id)), 6000)
  }

  const loadLists = useCallback(async () => {
    if (loadingRef.current) return
    loadingRef.current = true
    try {
      const list = await api<{ projects: ProjectSummary[] }>('/api/projects', undefined, 'GET')
      const briefData = await api<PortfolioBrief>('/api/brief', undefined, 'GET')
      setError('')
      setProjects(list.projects)
      setBrief(briefData)
      const projectDetails: Project[] = []
      for (const p of list.projects) {
        projectDetails.push(await api<Project>(`/api/projects/${p.id}`, undefined, 'GET'))
      }
      setDetails(projectDetails)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      loadingRef.current = false
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const data = await api<Info>('/api/info', undefined, 'GET')
        if (alive) setInfo(data)
      } catch (e) {
        if (alive) notify('err', e instanceof Error ? e.message : String(e))
      }
    })()
    return () => { alive = false }
  }, [])

  useEffect(() => {
    // Defer the fetch so the effect does not synchronously cascade state updates.
    queueMicrotask(() => { void loadLists() })
  }, [path, loadLists])

  const projectId = path.match(/^\/p\/([^/]+)/)?.[1]
  const projectName = projectId ? projects.find(p => p.id === projectId)?.client_name : undefined

  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <TopBar projectName={projectName} theme={theme} onToggleTheme={toggle} onAdd={() => navigate('/new')} />
      {info?.mode === 'sample' && <DemoBanner onReset={() => setResetOpen(true)} />}
      <main id="main" className="app-main">
        {projectId ? (
          <WorkbenchPage key={projectId} id={projectId} info={info} onChanged={loadLists} notify={notify} />
        ) : path === '/new' ? (
          <NewContractPage info={info} />
        ) : (
          <OverviewPage projects={projects} details={details} brief={brief} loading={loading} error={error}
            onRetry={() => { setLoading(true); setError(''); void loadLists() }} onAdd={() => navigate('/new')} />
        )}
      </main>
      <ToastStack toasts={toasts} onDismiss={id => setToasts(all => all.filter(t => t.id !== id))} />
      <Dialog open={resetOpen} title="Reset demo view?" confirmLabel="Reset view"
        onCancel={() => setResetOpen(false)}
        onConfirm={() => { setResetOpen(false); navigate('/'); notify('ok', 'Demo view reset. No projects or invoices were deleted.') }}>
        <p>This only clears the current view and returns to the portfolio. It does not delete projects, plans, or invoices.</p>
      </Dialog>
    </>
  )
}
