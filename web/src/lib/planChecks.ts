import { formatMoney, sumMinor, toMinor } from './money'
import { todayIso } from './dates'

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

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]
const MONTHS_SHORT = MONTHS.map(month => month.slice(0, 3))

const PUNCT: Record<string, string> = {
  '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
  '\u2013': '-', '\u2014': '-', '\u00a0': ' ',
}

function normalize(value: string): string {
  return value
    .replace(/[\u2018\u2019\u201c\u201d\u2013\u2014\u00a0]/g, char => PUNCT[char] ?? char)
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

/** The same common date spellings the backend accepts in an evidence quote. */
export function dateVariants(iso: string): string[] {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (!match) return [iso]
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  if (month < 1 || month > 12 || day < 1 || day > 31) return [iso]
  const date = new Date(Date.UTC(year, month - 1, day))
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
    return [iso]
  }
  const long = MONTHS[month - 1]
  const short = MONTHS_SHORT[month - 1]
  const paddedDay = String(day).padStart(2, '0')
  const paddedMonth = String(month).padStart(2, '0')
  return Array.from(new Set([
    iso,
    `${day} ${long} ${year}`, `${paddedDay} ${long} ${year}`,
    `${day} ${short} ${year}`, `${paddedDay} ${short} ${year}`,
    `${long} ${day}, ${year}`, `${short} ${day}, ${year}`,
    `${long} ${paddedDay}, ${year}`, `${short} ${paddedDay}, ${year}`,
    `${paddedDay}/${paddedMonth}/${year}`, `${paddedMonth}/${paddedDay}/${year}`,
  ]))
}

/** Compare the amount to numbers in the quote, so "USD 1,200" matches 1200.00. */
function amountInQuote(amount: string, quote: string): boolean {
  let wanted: number
  try {
    wanted = toMinor(amount)
  } catch {
    return false
  }
  const tokens = quote.match(/\d[\d,]*(?:\.\d+)?/g) ?? []
  return tokens.some(token => {
    try {
      return toMinor(token.replace(/,/g, '')) === wanted
    } catch {
      return false
    }
  })
}

export function checkPlan(contract: string, draft: PlanDraftLike, now = new Date()): PlanCheck[] {
  const today = todayIso(now)
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
    const amountOk = amountInQuote(m.amount, quote)
    const dateOk = dateVariants(m.due_date).map(normalize).some(variant => quote.includes(variant))
    const range = /\b(up to|between|maximum|max\.?|minimum|min\.?|no more than|not to exceed|range)\b/.test(quote)
      || /(?:usd|\$)\s*\d[\d,.]*\s*(?:-|to)\s*(?:usd|\$)?\s*\d/.test(quote)
    return !amountOk || !dateOk || range
  })
  const currencyOk = draft.currency === 'USD' && draft.milestones.every(m => m.amount && m.amount.trim() !== '')

  return [
    { key: 'currency', label: 'Currency', ok: currencyOk, detail: currencyOk ? 'USD' : 'Currency must be USD' },
    { key: 'sum', label: 'Sum', ok: sumOk, detail: sumDetail },
    { key: 'dates', label: 'Dates', ok: badDates.length === 0, detail: badDates.length ? `${badDates.length} date problem${badDates.length === 1 ? '' : 's'}` : 'All dates valid' },
    { key: 'quotes', label: 'Quotes', ok: quoteIssues.length === 0, detail: quoteIssues.length ? `${quoteIssues.length} quote problem${quoteIssues.length === 1 ? '' : 's'}` : `${draft.milestones.length} of ${draft.milestones.length} verbatim` },
  ]
}
