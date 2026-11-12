import { formatDue, todayIso } from './dates'

export type MilestoneKind = 'paid' | 'sent' | 'overdue' | 'draft' | 'locked'
export type PrimaryAction = 'invoice' | 'send' | 'check' | null

export type MilestoneLike = {
  id: string
  seq: number
  status: string
  due_date: string
  invoice_id: string | null
  hold: string | null
  op_state: string
}

export type PlanLike = { milestones: MilestoneLike[] }

export type MilestoneView = {
  kind: MilestoneKind
  primaryAction: PrimaryAction
  active: boolean
  dueLabel: string
  unlockReason?: string
}

export function deriveMilestoneView(plan: PlanLike, milestone: MilestoneLike, invoice: { id: string } | null, now: Date): MilestoneView {
  const today = todayIso(now)
  const prior = plan.milestones.find(m => m.seq < milestone.seq && m.status !== 'PAID')
  const due = milestone.due_date < today
  const dueLabel = due && milestone.status === 'SENT' ? `Overdue since ${formatDue(milestone.due_date)}` : `Due ${formatDue(milestone.due_date)}`

  if (milestone.status === 'PAID') {
    return { kind: 'paid', primaryAction: null, active: false, dueLabel }
  }
  if (milestone.hold) {
    return { kind: 'locked', primaryAction: null, active: false, dueLabel, unlockReason: `On hold: ${milestone.hold}` }
  }
  if (milestone.status === 'SENT') {
    return {
      kind: due ? 'overdue' : 'sent',
      primaryAction: 'check',
      active: true,
      dueLabel,
    }
  }
  if (milestone.status === 'DRAFTED') {
    return { kind: 'draft', primaryAction: 'send', active: true, dueLabel }
  }
  if (milestone.status === 'PARTIAL' || milestone.status === 'MISMATCH') {
    return { kind: 'overdue', primaryAction: 'check', active: true, dueLabel }
  }
  if (milestone.status === 'REFUNDED' || milestone.status === 'CANCELLED') {
    return { kind: 'locked', primaryAction: null, active: false, dueLabel, unlockReason: `Invoice ${milestone.status.toLowerCase()}.` }
  }
  if (prior) {
    return { kind: 'locked', primaryAction: null, active: false, dueLabel, unlockReason: `Unlocks when milestone ${prior.seq} is paid.` }
  }
  return {
    kind: 'draft',
    primaryAction: milestone.invoice_id || invoice ? 'send' : 'invoice',
    active: true,
    dueLabel,
  }
}
