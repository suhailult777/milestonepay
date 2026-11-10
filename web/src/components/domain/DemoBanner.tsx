import { FlaskConical } from 'lucide-react'
import { Button } from '../ui/Button'

const FULL = 'Demo mode. The contract and model output are fixtures and PayPal is simulated. No real funds move and no email is sent.'

export function DemoBanner({ onReset }: { onReset: () => void }) {
  return (
    <div className="demo-banner" role="note">
      <FlaskConical size={16} className="demo-icon" aria-hidden="true" />
      <p className="demo-copy">
        <span className="demo-long">{FULL}</span>
        <span className="demo-short">Demo mode, no real money</span>
      </p>
      <details className="demo-details">
        <summary>Details</summary>
        <p>{FULL}</p>
      </details>
      <Button variant="quiet" className="demo-reset" onClick={onReset}>Reset demo</Button>
    </div>
  )
}
