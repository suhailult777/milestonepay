import { useMemo, useState } from 'react'
import { ArrowRight, CircleCheck, FileText, Flag, Landmark, PencilLine, Plus, Send, ShieldCheck, Sparkles, UserRoundCheck } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Money } from '../../components/ui/Money'
import { MoneyBar } from '../../components/domain/MoneyBar'
import { formatDue, formatIstShort } from '../../lib/dates'
import { toMinor } from '../../lib/money'
import { navigate } from '../../lib/router'
import type { Audit, PortfolioBrief, Project, ProjectSummary } from '../../types'

type Filter = 'all' | 'needs' | 'paid'

type ActivityRow = {
  key: string
  project: string
  label: string
  action: string
  at: number
}

function activityLabel(event: Audit): string {
  const milestone = typeof event.detail.milestone === 'number' ? ` ${event.detail.milestone}` : ''
  switch (event.action) {
    case 'proposed_plan': return 'Plan proposed'
    case 'approved_plan': return 'Plan approved'
    case 'edited_plan': return event.detail.status === 'BLOCKED' ? 'Plan edit blocked by checks' : 'Plan edited'
    case 'drafted_invoice': return `Invoice drafted for milestone${milestone}`
    case 'sent_invoice': return `Invoice sent for milestone${milestone}`
    case 'reconciled': return event.detail.result === 'PAID' ? `PayPal confirmed milestone${milestone} paid` : `PayPal checked milestone${milestone}`
    case 'risk_reviewed': return 'Risk review saved'
    default: return event.action.replaceAll('_', ' ')
  }
}

function ActivityIcon({ action }: { action: string }) {
  const size = 15
  if (action === 'reconciled') return <CircleCheck size={size} aria-hidden="true" />
  if (action === 'sent_invoice') return <Send size={size} aria-hidden="true" />
  if (action === 'drafted_invoice') return <FileText size={size} aria-hidden="true" />
  if (action === 'edited_plan') return <PencilLine size={size} aria-hidden="true" />
  if (action === 'risk_reviewed') return <Flag size={size} aria-hidden="true" />
  if (action === 'approved_plan') return <UserRoundCheck size={size} aria-hidden="true" />
  return <Sparkles size={size} aria-hidden="true" />
}

export function OverviewPage({ projects = [], details = [], brief, loading, error, onRetry, onAdd }:
  {
    projects: ProjectSummary[]
    details: Project[]
    brief: PortfolioBrief | null
    loading: boolean
    error: string
    onRetry: () => void
    onAdd: () => void
  }) {
  const [filter, setFilter] = useState<Filter>('all')
  const needs = projects.filter(p => p.needs_action !== 'Complete').length
  const detailMap = useMemo(() => new Map(details.map(p => [p.id, p])), [details])
  const activity = useMemo<ActivityRow[]>(() => details
    .flatMap(project => project.audit.map(event => ({
      key: `${project.id}-${event.at}-${event.action}`,
      project: project.client_name,
      label: activityLabel(event),
      action: event.action,
      at: event.at,
    })))
    .sort((a, b) => b.at - a.at)
    .slice(0, 8), [details])
  const rows = useMemo(() => projects.filter(p => {
    if (filter === 'needs') return p.needs_action !== 'Complete'
    if (filter === 'paid') return p.paid_count === p.milestone_count && p.milestone_count > 0
    return true
  }), [projects, filter])

  if (loading) return <div className="overview"><h1>Portfolio</h1><p className="muted">Loading projects...</p></div>
  if (error) {
    return (
      <div className="overview">
        <h1>Portfolio</h1>
        <div className="state-box"><p>Couldn&apos;t load your projects. Check that the API is running, then retry.</p><Button onClick={onRetry}>Retry</Button></div>
      </div>
    )
  }
  if (!projects.length) {
    return (
      <div className="overview">
        <h1>Portfolio</h1>
        <div className="state-box">
          <p>No contracts yet. Add a contract or try the demo contract.</p>
          <div className="state-actions"><Button variant="primary" onClick={onAdd}><Plus size={16} /> Add contract</Button></div>
        </div>
      </div>
    )
  }

  let received = 0
  let awaiting = 0
  let locked = 0
  for (const project of details) {
    for (const m of project.milestones) {
      if (m.status === 'PAID') received += toMinor(m.amount)
      else if (m.status === 'SENT' || m.status === 'PARTIAL' || m.status === 'MISMATCH') awaiting += toMinor(m.amount)
      else if (m.status === 'PLANNED' || m.status === 'DRAFTED') locked += toMinor(m.amount)
    }
  }
  if (!details.length && brief) {
    received = toMinor(brief.collected_total)
    locked = toMinor(brief.outstanding_total)
  }

  return (
    <div className="overview">
      <h1>Portfolio</h1>
      <div className="overview-figures">
        <div><span className="figure-label">Received</span><Money amountMinor={received} size="xl" tone={received > 0 ? 'paid' : 'muted'} /></div>
        <div><span className="figure-label">Awaiting PayPal</span><Money amountMinor={awaiting} size="lg" /></div>
        <div><span className="figure-label">Still locked</span><Money amountMinor={locked} size="lg" tone="muted" /></div>
      </div>

      <div className="overview-chain" aria-label="Trust boundary">
        <span><Sparkles size={16} /> Model proposes</span>
        <span><ShieldCheck size={16} /> Code checks</span>
        <span><UserRoundCheck size={16} /> You approve</span>
        <span><Landmark size={16} /> PayPal confirms</span>
      </div>

      <div className="overview-lower">
        <section className="projects-section">
          <div className="section-head">
            <h2>Projects</h2>
            <div className="filters" role="group" aria-label="Filter projects">
              <Button variant={filter === 'needs' ? 'primary' : 'quiet'} onClick={() => setFilter('needs')}>Needs you {needs}</Button>
              <Button variant={filter === 'all' ? 'primary' : 'quiet'} onClick={() => setFilter('all')}>All</Button>
              <Button variant={filter === 'paid' ? 'primary' : 'quiet'} onClick={() => setFilter('paid')}>Paid</Button>
            </div>
          </div>
          <table className="projects-table">
            <thead><tr><th scope="col">Client</th><th scope="col">Milestones</th><th scope="col">Paid of total</th><th scope="col">Next action</th></tr></thead>
            <tbody>
              {rows.map(p => {
                const complete = p.paid_count === p.milestone_count && p.milestone_count > 0
                const detail = detailMap.get(p.id)
                const next = detail?.milestones.find(m => m.status !== 'PAID')
                const subline = next
                  ? `Next: ${next.title}, due ${formatDue(next.due_date)}`
                  : complete ? 'All milestones paid' : p.needs_action
                return (
                  <tr key={p.id}>
                    <td className="client-cell">
                      <a href={`/p/${p.id}`} onClick={e => { e.preventDefault(); navigate(`/p/${p.id}`) }}>{p.client_name}</a>
                      <span className="project-next">{subline}</span>
                    </td>
                    <td className="bar-cell">{detail ? <MoneyBar milestones={detail.milestones} showLabels={false} /> : <span className="muted small">No milestones</span>}</td>
                    <td><span className="paid-of"><Money amountMinor={toMinor(p.paid_total)} size="sm" tone={toMinor(p.paid_total) > 0 ? 'paid' : 'muted'} /> of <Money amountMinor={toMinor(p.total)} size="sm" /></span></td>
                    <td><a className="next-action" href={`/p/${p.id}`} onClick={e => { e.preventDefault(); navigate(`/p/${p.id}`) }}>{complete ? 'Complete' : p.needs_action}<ArrowRight size={14} /></a></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>

        <section className="activity-section" aria-label="Recent activity">
          <div className="activity-sheet">
            <div className="activity-head">
              <h2>Recent activity</h2>
              <span className="muted small">{activity.length} event{activity.length === 1 ? '' : 's'}</span>
            </div>
            {activity.length ? (
              <ol className="activity-list">
                {activity.map(item => (
                  <li className="activity-item" key={item.key}>
                    <span className={`activity-icon ${item.action === 'reconciled' ? 'is-paid' : ''}`}>
                      <ActivityIcon action={item.action} />
                    </span>
                    <span className="activity-copy">
                      <span className="activity-label">{item.label}</span>
                      <span className="activity-meta">{item.project}, {formatIstShort(item.at)}</span>
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="activity-empty muted">No activity yet. Approve a plan or send an invoice to start the record.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
