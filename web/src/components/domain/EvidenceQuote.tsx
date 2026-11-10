import { Quote } from 'lucide-react'
import { formatDue } from '../../lib/dates'
import { StatusChip } from './StatusChip'

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function terms(amount: string, date: string): string[] {
  const clean = amount.replace(/,/g, '')
  const dateText = formatDue(date)
  return Array.from(new Set([amount, clean, clean.replace(/\.00$/, ''), amount.replace(/\.00$/, ''), date, dateText]))
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
}

export function EvidenceQuote({ text, amount, date, tone = 'marker', showCaption = true, onShow }:
  { text: string; amount: string; date: string; tone?: 'marker' | 'danger'; showCaption?: boolean; onShow?: () => void }) {
  const words = terms(amount, date)
  const pattern = new RegExp(`(${words.map(escapeRegExp).join('|')})`, 'gi')
  const parts = words.length ? text.split(pattern) : [text]
  const lower = new Set(words.map(word => word.toLowerCase()))
  return (
    <blockquote className={`ui-quote ui-quote-${tone}`}>
      <p>{parts.map((part, i) => lower.has(part.toLowerCase())
        ? <mark key={i} className="ui-quote-mark">{part}</mark>
        : <span key={i}>{part}</span>)}</p>
      {(showCaption || onShow) && (
        <footer className="ui-quote-foot">
          {showCaption && <StatusChip state="verified" />}
          {onShow && <button type="button" className="ui-button ui-button-quiet" onClick={onShow}><Quote size={14} /> Show in contract</button>}
        </footer>
      )}
    </blockquote>
  )
}
