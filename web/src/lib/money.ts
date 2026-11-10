export type MoneyParts = { num: string; cur: string }

export function toMinor(amount: string): number {
  const clean = amount.replace(/,/g, '').trim()
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) {
    throw new Error(`Invalid money amount: ${amount}`)
  }
  const [whole, fraction = ''] = clean.split('.')
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'))
}

export function sumMinor(milestones: { amount: string }[]): number {
  return milestones.reduce((total, milestone) => total + toMinor(milestone.amount), 0)
}

export function formatMoney(minor: number, currency: 'USD' = 'USD'): MoneyParts {
  if (!Number.isInteger(minor)) throw new Error('Money must be integer minor units')
  return {
    num: new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(minor / 100),
    cur: currency,
  }
}
