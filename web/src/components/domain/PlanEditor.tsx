import { Button } from '../ui/Button'
import { EvidenceQuote } from './EvidenceQuote'
import { StatusChip } from './StatusChip'
import type { PlanDraft } from '../../types'
import type { PlanCheck } from '../../lib/planChecks'

export function PlanEditor({ draft, checks, busy, onChange, onSave, onCancel, onReextract }:
  {
    draft: PlanDraft
    checks: PlanCheck[]
    busy: string
    onChange: (patch: Partial<PlanDraft>) => void
    onSave: () => void
    onCancel: () => void
    onReextract: () => void
  }) {
  const allOk = checks.every(check => check.ok)
  const identityOk = draft.client_name.trim() !== '' && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(draft.client_email.trim())
  const ready = allOk && identityOk
  const fixReason = !identityOk ? 'Add a client name and a valid email.' : 'Fix the failed checks before saving.'
  const disabled = ready ? {} : { disabled: true as const, disabledReason: fixReason }
  const updateMilestone = (id: string, patch: Partial<PlanDraft['milestones'][number]>) => {
    onChange({ milestones: draft.milestones.map(m => m.id === id ? { ...m, ...patch } : m) })
  }
  return (
    <div className="plan-editor">
      <div className="plan-editor-head">
        <div><h3>Edit plan</h3><p className="muted small">Evidence stays locked. Fix the source contract and re-extract if a quote is wrong.</p></div>
        <Button variant="quiet" onClick={onReextract}>Re-extract from contract</Button>
      </div>
      <div className="plan-identity">
        <label className="ui-field plan-total">Client name
          <input className="ui-input" value={draft.client_name} onChange={e => onChange({ client_name: e.target.value })} />
        </label>
        <label className="ui-field plan-total">Client email
          <input className="ui-input" type="email" value={draft.client_email} onChange={e => onChange({ client_email: e.target.value })} />
        </label>
      </div>
      <label className="ui-field plan-total">Total (USD)
        <input className="ui-input" value={draft.total} onChange={e => onChange({ total: e.target.value })} />
      </label>
      <div className="plan-edit-rows">
        {draft.milestones.map((m, i) => (
          <div className="plan-edit-row" key={m.id}>
            <div className="plan-edit-fields">
              <label className="ui-field">Title
                <input className="ui-input" value={m.title} onChange={e => updateMilestone(m.id, { title: e.target.value })} />
              </label>
              <label className="ui-field">Amount
                <input className="ui-input" value={m.amount} onChange={e => updateMilestone(m.id, { amount: e.target.value })} />
              </label>
              <label className="ui-field">Due date
                <input className="ui-input" type="date" value={m.due_date} onChange={e => updateMilestone(m.id, { due_date: e.target.value })} />
              </label>
            </div>
            <div className="plan-locked-quote">
              <EvidenceQuote text={m.evidence} amount={m.amount} date={m.due_date} showCaption={false} />
              <div className="plan-lock-line">
                <StatusChip state="locked" label={`Evidence locked for milestone ${i + 1}`} />
                <span className="muted tiny">Amounts and dates must appear in this text.</span>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="plan-editor-actions">
        <Button variant="primary" {...disabled} loading={busy === 'Saving plan'} onClick={onSave}>Save changes</Button>
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        {!ready && <span className="disabled-reason">{fixReason}</span>}
        {ready && <span className="muted small">Saving does not approve the plan.</span>}
      </div>
    </div>
  )
}
