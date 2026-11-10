import { Flag } from 'lucide-react'
import { Button } from '../ui/Button'
import { EvidenceQuote } from './EvidenceQuote'
import { StatusChip, type ChipState } from './StatusChip'
import type { RiskNote } from '../../types'

function stateFor(severity: string): ChipState {
  if (severity === 'high') return 'risk-high'
  if (severity === 'low') return 'risk-low'
  return 'risk-medium'
}

export function RiskFlag({ note, onShowInText }: { note: RiskNote; onShowInText: (quote: string) => void }) {
  return (
    <article className="risk-flag">
      <div className="risk-flag-head">
        <span className="risk-flag-icon"><Flag size={18} /></span>
        <h3>{note.title}</h3>
        <StatusChip state={stateFor(note.severity)} />
      </div>
      <EvidenceQuote text={note.evidence} amount="" date="" tone="danger" showCaption={false} />
      <p><strong>Why it matters:</strong> {note.why}</p>
      <p><strong>Ask the client:</strong> {note.question}</p>
      <Button variant="quiet" onClick={() => onShowInText(note.evidence)}>Show in text</Button>
    </article>
  )
}
