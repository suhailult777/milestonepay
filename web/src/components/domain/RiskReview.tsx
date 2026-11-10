import { Button } from '../ui/Button'
import { RiskFlag } from './RiskFlag'
import type { RiskReview } from '../../types'

export function RiskReviewPanel({ risk, onRun, onShowInText }:
  { risk: RiskReview | null; onRun: () => void; onShowInText: (quote: string) => void }) {
  if (!risk) {
    return (
      <div className="risk-review">
        <p className="muted">No review yet. The model can flag payment and scope risks, but only with a quote from the contract.</p>
        <Button variant="primary" onClick={onRun}>Review contract risks</Button>
      </div>
    )
  }
  return (
    <div className="risk-review">
      <p className="muted">{risk.summary || 'Review complete.'}</p>
      {risk.risks.length === 0 && (
        <p>No risky clauses found in the text the model reviewed. Read the contract yourself before you approve.</p>
      )}
      {risk.risks.map(note => <RiskFlag key={note.title} note={note} onShowInText={onShowInText} />)}
      <div className="risk-review-foot">
        <p className="muted small">Flags are advice. They do not change the plan. Only you can approve it.</p>
        <Button variant="quiet" onClick={onRun}>Re-run review</Button>
      </div>
    </div>
  )
}
