import { describe, expect, it } from 'vitest'
import { checkPlan } from './planChecks'

const contract = 'Milestone 1: Design, USD 400, due 2026-11-20.\nMilestone 2: Build, USD 700, due 2026-12-05.'
const base = {
  total: '1100.00',
  currency: 'USD',
  milestones: [
    { amount: '400.00', due_date: '2026-11-20', evidence: 'Milestone 1: Design, USD 400, due 2026-11-20.' },
    { amount: '700.00', due_date: '2026-12-05', evidence: 'Milestone 2: Build, USD 700, due 2026-12-05.' },
  ],
}
const today = new Date('2026-11-10T00:00:00Z')

describe('checkPlan', () => {
  it('passes a clean plan', () => {
    expect(checkPlan(contract, base, today).map(c => c.ok)).toEqual([true, true, true, true])
  })

  it('fails a sum mismatch', () => {
    expect(checkPlan(contract, { ...base, total: '1200.00' }, today).find(c => c.key === 'sum')).toMatchObject({
      ok: false, detail: '1,100.00 differs from total 1,200.00',
    })
  })

  it('fails when the amount is not in its quote', () => {
    const changed = { ...base, milestones: [{ ...base.milestones[0], amount: '800.00' }, base.milestones[1]] }
    expect(checkPlan(contract, changed, today).find(c => c.key === 'quotes')).toMatchObject({ ok: false })
  })

  it('fails a past date', () => {
    const changed = { ...base, milestones: [{ ...base.milestones[0], due_date: '2026-10-01' }, base.milestones[1]] }
    expect(checkPlan(contract, changed, today).find(c => c.key === 'dates')).toMatchObject({ ok: false })
  })

  it('fails a non-USD plan', () => {
    expect(checkPlan(contract, { ...base, currency: 'EUR' }, today).find(c => c.key === 'currency')).toMatchObject({ ok: false })
  })
})
