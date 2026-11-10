import { toMinor } from '../../lib/money'
import { deriveMilestoneView, type MilestoneLike } from '../../lib/milestoneState'
import { useNow } from '../../lib/useNow'
import type { Milestone } from '../../types'

export function MoneyBar({ milestones = [], showLabels = true, justPaid = null }: { milestones: Milestone[]; showLabels?: boolean; justPaid?: string | null }) {
  const safe = milestones.filter((m): m is Milestone => Boolean(m && m.amount))
  const total = safe.reduce((sum, m) => sum + toMinor(m.amount), 0)
  const now = useNow()
  const plan = { milestones: safe }
  const segments = safe.map(m => {
    const view = deriveMilestoneView(plan as { milestones: MilestoneLike[] }, m, m.invoice_id ? { id: m.invoice_id } : null, now)
    const share = total ? (toMinor(m.amount) / total) * 100 : 0
    return { m, view, share }
  })
  return (
    <div className="money-bar-wrap">
      <div className="money-bar" role="img" aria-label="Milestone payment state">
        {segments.map(({ m, view, share }) => (
          <span key={m.id} className={`money-seg money-seg-${view.kind} ${justPaid === m.id ? 'is-just-paid' : ''}`}
            style={{ flexBasis: `${share}%` }}
            title={`Milestone ${m.seq}, ${m.amount} USD, ${view.kind}`} />
        ))}
      </div>
      {showLabels && (
        <div className="money-labels" aria-hidden="true">
          {segments.map(({ m, view }) => (
            <span key={m.id} style={{ flexBasis: `${(toMinor(m.amount) / (total || 1)) * 100}%` }}>
              {m.seq} {view.kind === 'paid' ? 'Paid' : view.kind === 'sent' ? 'Sent' : view.kind === 'overdue' ? 'Overdue' : view.kind === 'draft' ? 'Draft' : 'Locked'}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
