import { CircleAlert, CircleCheck } from 'lucide-react'
import type { PlanCheck } from '../../lib/planChecks'

export function ChecksBar({ checks }: { checks: PlanCheck[] }) {
  return (
    <div className="checks-bar" role="status">
      {checks.map(check => (
        <span key={check.key} className={`check ${check.ok ? 'check-ok' : 'check-bad'}`}>
          {check.ok ? <CircleCheck size={14} aria-hidden="true" /> : <CircleAlert size={14} aria-hidden="true" />}
          <strong>{check.label}</strong>
          <span>{check.detail}</span>
        </span>
      ))}
    </div>
  )
}
