import { Flag, PencilLine, UserRoundCheck } from 'lucide-react'
import { Button } from '../ui/Button'
import { ChecksBar } from './ChecksBar'
import { MilestoneRow } from './MilestoneRow'
import { PlanEditor } from './PlanEditor'
import { deriveMilestoneView, type MilestoneLike } from '../../lib/milestoneState'
import { formatIst } from '../../lib/dates'
import { useNow } from '../../lib/useNow'
import type { PlanCheck } from '../../lib/planChecks'
import type { Milestone, PlanDraft, Project } from '../../types'

export function Ledger({ project, activeId, busy, justPaid, editing, draft, checks, onSelect, onShowEvidence, onApprove, onEdit, onCancelEdit, onSaveEdit, onChangeDraft, onReextract, onDraft, onSend, onCheck, onViewRisk }:
  {
    project: Project
    activeId: string | null
    busy: string
    justPaid?: string | null
    editing: boolean
    draft: PlanDraft | null
    checks: PlanCheck[]
    onSelect: (id: string) => void
    onShowEvidence: (id: string) => void
    onApprove: () => void
    onEdit: () => void
    onCancelEdit: () => void
    onSaveEdit: () => void
    onChangeDraft: (patch: Partial<PlanDraft>) => void
    onReextract: () => void
    onDraft: (m: Milestone) => void
    onSend: (m: Milestone) => void
    onCheck: (m: Milestone) => void
    onViewRisk: () => void
  }) {
  const now = useNow()
  const views = project.milestones.map(m => ({
    m,
    view: deriveMilestoneView(project as { milestones: MilestoneLike[] }, m, m.invoice_id ? { id: m.invoice_id } : null, now),
  }))
  const firstActive = views.find(x => x.view.active)?.m.id ?? null
  const selected = activeId ?? firstActive
  const approved = project.audit.find(a => a.action === 'approved_plan')
  const canApprove = checks.length > 0 && checks.every(check => check.ok)
  const approveDisabled = canApprove ? {} : { disabled: true as const, disabledReason: 'Fix the failed checks before approving.' }

  return (
    <section className="ledger-sheet" aria-label="Milestones">
      <div className="ledger-head">
        <h2>Milestones</h2>
        <span className="muted small">{project.milestones.filter(m => m.status === 'PAID').length} of {project.milestones.length} paid</span>
      </div>

      {(project.status === 'PROPOSED' || project.status === 'BLOCKED') && (
        <>
          <ChecksBar checks={checks} />
          {editing && draft ? (
            <PlanEditor draft={draft} checks={checks} busy={busy} onChange={onChangeDraft}
              onSave={onSaveEdit} onCancel={onCancelEdit} onReextract={onReextract} />
          ) : (
            <div className="plan-bar">
              <div><strong>{project.status === 'BLOCKED' ? 'Plan blocked.' : 'Plan proposed.'}</strong> <span className="muted">Every amount and date must pass the fixed checks.</span></div>
              <div className="plan-bar-actions">
                <Button variant="secondary" onClick={onEdit}><PencilLine size={16} /> Edit plan</Button>
                <Button variant="primary" {...approveDisabled} loading={busy === 'Approving plan'} onClick={onApprove}>Approve plan</Button>
                {!canApprove && <span className="disabled-reason">Fix the failed checks before approving.</span>}
              </div>
            </div>
          )}
        </>
      )}
      {approved && (
        <p className="receipt"><span className="receipt-icon"><UserRoundCheck size={15} /></span> Plan approved by you, {formatIst(approved.at)}. Editing is locked.</p>
      )}

      {project.risk && (
        <button type="button" className="risk-row" onClick={onViewRisk}>
          <Flag size={16} className="risk-row-icon" aria-hidden="true" />
          <span>{project.risk.risks.length} risk{project.risk.risks.length === 1 ? '' : 's'} to resolve</span>
          <span className="risk-row-view">View</span>
        </button>
      )}

      {!(editing && draft) && (
        project.milestones.length === 0 ? (
          <p className="state-box">No milestones yet. The model proposes them from the contract.</p>
        ) : (
          <ol className="milestone-list">
            {views.map(({ m, view }) => (
              <MilestoneRow key={m.id} milestone={m} view={view} expanded={selected === m.id}
                justPaid={justPaid === m.id}
                onSelect={() => onSelect(m.id)} onShowEvidence={() => onShowEvidence(m.id)}>
                {view.primaryAction === 'invoice' && (
                  <Button variant="primary" loading={busy === 'Creating invoice'} onClick={() => onDraft(m)}>Create invoice</Button>
                )}
                {view.primaryAction === 'send' && (
                  <Button variant="primary" onClick={() => onSend(m)}>Send invoice</Button>
                )}
                {view.primaryAction === 'check' && (
                  <Button variant="secondary" loading={busy === 'Checking PayPal'} onClick={() => onCheck(m)}>Check with PayPal</Button>
                )}
                {m.status === 'PAID' && m.pay_link && (
                  <a className="ui-button ui-button-secondary" href={m.pay_link} target="_blank" rel="noreferrer">Open payer link</a>
                )}
              </MilestoneRow>
            ))}
          </ol>
        )
      )}
    </section>
  )
}
