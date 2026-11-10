import { describe, expect, it } from 'vitest'
import { deriveMilestoneView, type MilestoneLike, type PlanLike } from './milestoneState'

const today = new Date('2026-11-10T00:00:00Z')

function m(seq: number, status: string, due = '2026-12-01', patch: Partial<MilestoneLike> = {}): MilestoneLike {
  return { id: `m${seq}`, seq, status, due_date: due, invoice_id: null, hold: null, op_state: 'NONE', ...patch }
}

function plan(...milestones: MilestoneLike[]): PlanLike {
  return { milestones }
}

describe('deriveMilestoneView', () => {
  it('paid row has no primary action', () => {
    const paid = m(1, 'PAID')
    expect(deriveMilestoneView(plan(paid), paid, null, today)).toMatchObject({ kind: 'paid', primaryAction: null, active: false })
  })

  it('second milestone is locked while first is sent', () => {
    const sent = m(1, 'SENT')
    const second = m(2, 'PLANNED')
    expect(deriveMilestoneView(plan(sent, second), second, null, today)).toMatchObject({
      kind: 'locked', primaryAction: null, active: false, unlockReason: 'Unlocks when milestone 1 is paid.',
    })
  })

  it('sent past due is overdue', () => {
    const paid = m(1, 'PAID')
    const overdue = m(2, 'SENT', '2026-11-01')
    expect(deriveMilestoneView(plan(paid, overdue), overdue, { id: 'INV' }, today)).toMatchObject({
      kind: 'overdue', primaryAction: 'check', dueLabel: 'Overdue since 1 Nov 2026',
    })
  })

  it('draft offers send', () => {
    const paid = m(1, 'PAID')
    const draft = m(2, 'DRAFTED', '2026-12-01', { invoice_id: 'INV' })
    expect(deriveMilestoneView(plan(paid, draft), draft, { id: 'INV' }, today)).toMatchObject({ kind: 'draft', primaryAction: 'send' })
  })

  it('unlocked planned milestone offers invoice creation', () => {
    const paid = m(1, 'PAID')
    const planned = m(2, 'PLANNED')
    expect(deriveMilestoneView(plan(paid, planned), planned, null, today)).toMatchObject({
      kind: 'draft', primaryAction: 'invoice', active: true,
    })
  })

  it('hold becomes locked with a reason', () => {
    const held = m(1, 'PLANNED', '2026-12-01', { hold: 'earlier milestone refunded' })
    expect(deriveMilestoneView(plan(held), held, null, today)).toMatchObject({
      kind: 'locked', unlockReason: 'On hold: earlier milestone refunded',
    })
  })
})
