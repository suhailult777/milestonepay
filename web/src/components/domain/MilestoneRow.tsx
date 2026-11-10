import { CircleCheck, LockKeyhole } from 'lucide-react'
import type { ReactNode } from 'react'
import { EvidenceQuote } from './EvidenceQuote'
import { Money } from '../ui/Money'
import { StatusChip, type ChipState } from './StatusChip'
import type { MilestoneLike, MilestoneView } from '../../lib/milestoneState'
import { toMinor } from '../../lib/money'

const CHIP: Record<MilestoneView['kind'], ChipState> = {
  paid: 'paid',
  sent: 'sent',
  overdue: 'overdue',
  draft: 'draft',
  locked: 'locked',
}

export function MilestoneRow({ milestone, view, expanded, justPaid, onSelect, onShowEvidence, children }:
  {
    milestone: MilestoneLike & { title: string; amount: string; evidence: string; invoice_id: string | null }
    view: MilestoneView
    expanded: boolean
    justPaid?: boolean
    onSelect?: () => void
    onShowEvidence?: () => void
    children?: ReactNode
  }) {
  const locked = view.kind === 'locked'
  return (
    <li className={`milestone-row milestone-${view.kind} ${view.active ? 'is-active' : ''} ${justPaid ? 'is-just-paid' : ''}`} aria-current={view.active ? 'step' : undefined}>
      <button type="button" className="row-summary" onClick={onSelect} disabled={locked} aria-expanded={expanded}>
        <span className="row-index" aria-hidden="true">
          {view.kind === 'paid' ? <CircleCheck size={18} /> : locked ? <LockKeyhole size={16} /> : milestone.seq}
        </span>
        <span className="row-title">
          <span className="row-name">{milestone.title}</span>
          <span className="row-due">{view.dueLabel}</span>
          {view.unlockReason && <span className="row-unlock">{view.unlockReason}</span>}
        </span>
        <span className="row-state">
          <StatusChip state={CHIP[view.kind]} />
          <Money amountMinor={toMinor(milestone.amount)} size="md" tone={view.kind === 'paid' ? 'paid' : 'default'} />
        </span>
      </button>
      {expanded && !locked && (
        <div className="row-detail">
          <EvidenceQuote text={milestone.evidence} amount={milestone.amount} date={milestone.due_date} onShow={onShowEvidence} />
          {milestone.invoice_id && <p className="row-invoice mono">Invoice {milestone.invoice_id}</p>}
          {children && <div className="row-actions">{children}</div>}
        </div>
      )}
    </li>
  )
}
