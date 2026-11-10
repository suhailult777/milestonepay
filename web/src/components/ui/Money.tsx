import { formatMoney } from '../../lib/money'

export type MoneySize = 'sm' | 'md' | 'lg' | 'xl'
export type MoneyTone = 'default' | 'paid' | 'muted' | 'danger'

export function Money({ amountMinor, currency = 'USD', size = 'md', tone = 'default', className = '' }:
  { amountMinor: number; currency?: 'USD'; size?: MoneySize; tone?: MoneyTone; className?: string }) {
  const { num, cur } = formatMoney(amountMinor, currency)
  return (
    <span className={`ui-money ui-money-${size} ui-money-${tone} ${className}`.trim()}
      aria-label={`${num} ${cur === 'USD' ? 'US dollars' : cur}`}>
      <span className="ui-money-num">{num}</span>
      <span className="ui-money-cur">{cur}</span>
    </span>
  )
}
