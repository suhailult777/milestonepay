import { formatMoney, sumMinor, toMinor } from './money'
import { formatDue } from './dates'

export type PlanDraftLike = {
  total: string
  currency: string
  milestones: { amount: string; due_date: string; evidence: string }[]
}

export type PlanCheck = {
  key: 'currency' | 'sum' | 'dates' | 'quotes'
  label: string
  ok: boolean
  detail: string
}

function normalize(value: string): string {
  return value.replace(/\s+/g, ' ').trim().toLowerCase()
}

export function checkPlan(contract: string, draft: PlanDraftLike, now = new Date()): PlanCheck[] {
  const today = now.toISOString().slice(0, 10)
  let sumOk = false
  let sumDetail = 'Sum is not readable'
  try {
    const sum = sumMinor(draft.milestones)
    const total = toMinor(draft.total)
    sumOk = sum === total
    sumDetail = sumOk ? `${formatMoney(sum).num} equals the total` : `${formatMoney(sum).num} differs from total ${formatMoney(total).num}`
  } catch {
    sumOk = false
  }

  const badDates = draft.milestones.filter(m => !/^\d{4}-\d{2}-\d{2}$/.test(m.due_date) || m.due_date < today)
  const source = normalize(contract)
  const quoteIssues = draft.milestones.filter(m => {
    const quote = normalize(m.evidence)
    if (!quote || !source.includes(quote)) return true
    const amount = m.amount.replace(/\.00$/, '')
    const amountOk = quote.includes(amount.toLowerCase())
    const dateOk = quote.includes(m.due_date.toLowerCase()) || quote.includes(formatDue(m.due_date).toLowerCase())
    return !amountOk || !dateOk
  })
  const currencyOk = draft.currency === 'USD' && draft.milestones.every(m => m.amount && m.amount.trim() !== '')

  return [
    { key: 'currency', label: 'Currency', ok: currencyOk, detail: currencyOk ? 'USD' : 'Currency must be USD' },
    { key: 'sum', label: 'Sum', ok: sumOk, detail: sumDetail },
    { key: 'dates', label: 'Dates', ok: badDates.length === 0, detail: badDates.length ? `${badDates.length} date problem${badDates.length === 1 ? '' : 's'}` : 'All dates valid' },
    { key: 'quotes', label: 'Quotes', ok: quoteIssues.length === 0, detail: quoteIssues.length ? `${quoteIssues.length} quote problem${quoteIssues.length === 1 ? '' : 's'}` : `${draft.milestones.length} of ${draft.milestones.length} verbatim` },
  ]
}
