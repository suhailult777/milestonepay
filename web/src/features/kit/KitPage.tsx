import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Money } from '../../components/ui/Money'
import { Skeleton } from '../../components/ui/Skeleton'
import { StatusChip, type ChipState } from '../../components/domain/StatusChip'
import { MilestoneRow } from '../../components/domain/MilestoneRow'
import { deriveMilestoneView, type MilestoneLike, type PlanLike } from '../../lib/milestoneState'

const CHIPS: ChipState[] = [
  'paid', 'sent', 'overdue', 'draft', 'locked', 'proposed',
  'risk-low', 'risk-medium', 'risk-high', 'verified', 'failed',
]

type RowMilestone = MilestoneLike & { title: string; amount: string; evidence: string }

function row(id: string, seq: number, status: string, due: string, patch: Partial<RowMilestone> = {}): RowMilestone {
  return {
    id, seq, status, due_date: due, invoice_id: null, hold: null, op_state: 'NONE',
    title: `Milestone ${seq}`, amount: '400.00', evidence: `Milestone ${seq}: Work, USD 400, due ${due}.`,
    ...patch,
  }
}

const paid = row('paid-1', 1, 'PAID', '2026-11-20', { title: 'Design mockups', invoice_id: 'SIM-INV-1' })
const sent = row('sent-2', 2, 'SENT', '2026-12-05', { title: 'Working MVP', invoice_id: 'SIM-INV-2' })
const overdue = row('overdue-2', 2, 'SENT', '2026-11-01', { title: 'Working MVP', invoice_id: 'SIM-INV-3' })
const draft = row('draft-2', 2, 'DRAFTED', '2026-12-05', { title: 'Working MVP', invoice_id: 'SIM-INV-4' })
const locked = row('locked-2', 2, 'PLANNED', '2026-12-05', { title: 'Working MVP' })
const ready = row('ready-2', 2, 'PLANNED', '2026-12-05', { title: 'Working MVP' })

const ROWS: { plan: PlanLike; milestone: RowMilestone }[] = [
  { plan: { milestones: [paid] }, milestone: paid },
  { plan: { milestones: [paid, sent] }, milestone: sent },
  { plan: { milestones: [paid, overdue] }, milestone: overdue },
  { plan: { milestones: [paid, draft] }, milestone: draft },
  { plan: { milestones: [sent, locked] }, milestone: locked },
  { plan: { milestones: [paid, ready] }, milestone: ready },
]

export default function KitPage() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const forced = new URLSearchParams(location.search).get('theme')
    if (forced === 'light' || forced === 'dark') return forced
    return localStorage.getItem('mp-theme') === 'dark' ? 'dark' : 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('mp-theme', theme)
  }, [theme])
  useEffect(() => {
    if (new URLSearchParams(location.search).get('section') === 'rows') {
      document.querySelector('.milestone-list')?.scrollIntoView({ block: 'start' })
    }
  }, [])
  const [activeId, setActiveId] = useState(sent.id)
  return (
    <main className="kit-page">
      <header className="kit-head">
        <div>
          <h1>Proof Ledger kit</h1>
          <p>Primitives, chips, money, inputs, and states.</p>
        </div>
        <Button variant="quiet" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </Button>
      </header>

      <section className="kit-section">
        <h2>Buttons</h2>
        <div className="kit-row">
          <Button variant="primary">Send invoice</Button>
          <Button variant="secondary">Check with PayPal</Button>
          <Button variant="quiet">Retry</Button>
          <Button variant="primary" loading>Sending invoice</Button>
        </div>
        <div className="kit-row">
          <Button variant="primary" disabled disabledReason="Fix the date check first.">Approve plan</Button>
          <span className="kit-reason">Fix the date check first.</span>
        </div>
      </section>

      <section className="kit-section">
        <h2>Money</h2>
        <div className="kit-row kit-money-row">
          <Money amountMinor={150000} size="xl" />
          <Money amountMinor={70000} size="lg" />
          <Money amountMinor={40000} size="md" tone="paid" />
          <Money amountMinor={115000} size="sm" tone="muted" />
        </div>
      </section>

      <section className="kit-section">
        <h2>Status chips</h2>
        <div className="kit-row">
          {CHIPS.map(state => <StatusChip key={state} state={state} />)}
        </div>
      </section>

      <section className="kit-section">
        <h2>Inputs and skeleton</h2>
        <div className="kit-grid">
          <Input label="Client name" placeholder="Acme Labs" />
          <Input label="Billing email" placeholder="billing@example.com" />
          <Input label="Amount" defaultValue="abc" error="Enter a plain amount with up to 2 decimals." />
        </div>
        <div className="kit-skeleton">
          <Skeleton width="65%" />
          <Skeleton width="42%" />
          <Skeleton width="78%" />
        </div>
      </section>

      <section className="kit-section">
        <h2>Ledger rows</h2>
        <ol className="milestone-list">
          {ROWS.map(({ plan, milestone }) => {
            const view = deriveMilestoneView(plan, milestone, milestone.invoice_id ? { id: milestone.invoice_id } : null, new Date('2026-11-10T00:00:00Z'))
            return (
              <MilestoneRow key={milestone.id} milestone={milestone} view={view} expanded={activeId === milestone.id}
                onSelect={() => setActiveId(milestone.id)}>
                {view.primaryAction === 'send' && <Button variant="primary">Send invoice</Button>}
                {view.primaryAction === 'check' && <Button variant="secondary">Check with PayPal</Button>}
                {view.primaryAction === 'invoice' && <Button variant="primary">Create invoice</Button>}
              </MilestoneRow>
            )
          })}
        </ol>
      </section>
    </main>
  )
}
