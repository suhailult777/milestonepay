import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { api } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { Money } from '../../components/ui/Money'
import { ContractSheet } from '../../components/domain/ContractSheet'
import { Ledger } from '../../components/domain/Ledger'
import { MoneyBar } from '../../components/domain/MoneyBar'
import { TrustChain, TrustChainMobile } from '../../components/domain/TrustChain'
import { deriveMilestoneView, type MilestoneLike } from '../../lib/milestoneState'
import { formatDue } from '../../lib/dates'
import { toMinor } from '../../lib/money'
import { checkPlan } from '../../lib/planChecks'
import { navigate } from '../../lib/router'
import { useNow } from '../../lib/useNow'
import type { Info, Milestone, PlanDraft, Project } from '../../types'

export function WorkbenchPage({ id, info, onChanged, notify }:
  { id: string; info: Info | null; onChanged: () => Promise<void>; notify: (kind: 'ok' | 'err', text: string) => void }) {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [activeId, setActiveId] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [sendTarget, setSendTarget] = useState<Milestone | null>(null)
  const [justPaid, setJustPaid] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const [editingPlan, setEditingPlan] = useState(false)
  const [draft, setDraft] = useState<PlanDraft | null>(null)
  const [mobileTab, setMobileTab] = useState<'ledger' | 'contract' | 'risk'>('ledger')
  const [panelTab, setPanelTab] = useState<'contract' | 'risk'>(
    new URLSearchParams(location.search).get('tab') === 'risk' ? 'risk' : 'contract',
  )
  const now = useNow()

  const load = useCallback(async () => {
    try {
      const data = await api<Project>(`/api/projects/${id}`, undefined, 'GET')
      setProject(data)
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    // Defer the fetch so the effect does not synchronously cascade state updates.
    queueMicrotask(() => { void load() })
  }, [load])

  const run = async (label: string, fn: () => Promise<unknown>, success: string) => {
    setBusy(label)
    try {
      await fn()
      await load()
      await onChanged()
      notify('ok', success)
    } catch (e) {
      notify('err', e instanceof Error ? e.message : String(e))
      await load()
    } finally {
      setBusy('')
    }
  }

  const checkPaypal = async (m: Milestone) => {
    setBusy('Checking PayPal')
    try {
      const result = await api<{ outcome: string }>(`/api/milestones/${m.id}/refresh`, { approver: 'You' })
      await load()
      await onChanged()
      if (result.outcome === 'milestone_paid') {
        const next = (project?.milestones ?? []).find(x => x.seq > m.seq)
        setJustPaid(m.id)
        setAnnouncement(`Milestone ${m.seq} paid.${next ? ` Milestone ${next.seq} unlocked.` : ''}`)
        notify('ok', next ? `Milestone ${m.seq} paid. Milestone ${next.seq} unlocked.` : `Milestone ${m.seq} paid.`)
        window.setTimeout(() => setJustPaid(null), 1600)
      } else {
        notify('ok', `PayPal result: ${result.outcome}`)
      }
    } catch (e) {
      notify('err', e instanceof Error ? e.message : String(e))
      await load()
    } finally {
      setBusy('')
    }
  }

  const simulatePay = async (m: Milestone) => {
    setBusy('Simulating payment')
    try {
      const result = await api<{ outcome: string }>(`/api/simulate/pay/${m.id}`, {})
      await load()
      await onChanged()
      if (result.outcome === 'milestone_paid') {
        setJustPaid(m.id)
        const next = (project?.milestones ?? []).find(x => x.seq > m.seq)
        setAnnouncement(`Milestone ${m.seq} paid.${next ? ` Milestone ${next.seq} unlocked.` : ''}`)
        notify('ok', next ? `Milestone ${m.seq} paid. Milestone ${next.seq} unlocked.` : `Milestone ${m.seq} paid.`)
        window.setTimeout(() => setJustPaid(null), 1600)
      } else {
        notify('ok', `Simulated result: ${result.outcome}`)
      }
    } catch (e) {
      notify('err', e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  const simulateForged = async (m: Milestone) => {
    setBusy('Sending forged webhook')
    try {
      const result = await api<{ outcome: string }>(`/api/simulate/forged/${m.id}`, {})
      notify('ok', result.outcome === 'rejected' ? 'Forged webhook rejected. No state change.' : `Forged result: ${result.outcome}`)
    } catch (e) {
      notify('err', e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  const projectDraft: PlanDraft | null = project ? {
    client_name: project.client_name,
    client_email: project.client_email,
    total: project.total,
    currency: project.currency,
    milestones: project.milestones.map(m => ({
      id: m.id, title: m.title, amount: m.amount, due_date: m.due_date, evidence: m.evidence,
    })),
  } : null
  const currentDraft = draft ?? projectDraft
  const checks = project && currentDraft ? checkPlan(project.source_text, currentDraft) : []
  const canApprove = project?.status === 'PROPOSED' && checks.length > 0 && checks.every(check => check.ok)

  const startEdit = () => {
    if (!projectDraft) return
    setDraft(projectDraft)
    setEditingPlan(true)
  }

  const reviewRisk = () => {
    void run('Reviewing risks', () => api(`/api/projects/${id}/risk`, {}), 'Risk review saved. This is not legal advice.')
  }

  const savePlan = async () => {
    if (!project || !draft) return
    setBusy('Saving plan')
    try {
      const result = await api<{ project: Project; errors: string[] }>(`/api/projects/${id}/plan`, draft, 'PUT')
      setProject(result.project)
      setEditingPlan(false)
      setDraft(null)
      await onChanged()
      notify(result.errors.length ? 'err' : 'ok',
        result.errors.length ? `Saved, but ${result.errors.length} check${result.errors.length === 1 ? '' : 's'} still block approval.` : 'Plan updated.')
    } catch (e) {
      notify('err', e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  if (loading) return <div className="page-narrow"><p className="muted">Loading project...</p></div>
  if (error || !project) {
    return (
      <div className="page-narrow">
        <p>Couldn&apos;t load this project.</p>
        <p className="muted">{error}</p>
        <Button onClick={() => { setLoading(true); void load() }}>Retry</Button>
      </div>
    )
  }

  const received = project.milestones.filter(m => m.status === 'PAID').reduce((sum, m) => sum + toMinor(m.amount), 0)
  const next = project.milestones.find(m => m.status !== 'PAID')
  const sentMilestone = project.milestones.find(m => m.status === 'SENT')
  const nextView = next ? deriveMilestoneView(project as { milestones: MilestoneLike[] }, next, next.invoice_id ? { id: next.invoice_id } : null, now) : null
  const mobileAction = project.status === 'PROPOSED'
    ? (canApprove ? { label: 'Approve plan', run: () => void run('Approving plan', () => api(`/api/projects/${id}/approve`, { approver: 'You' }), 'Plan approved. Draft and send stay separate.') } : { label: 'Edit plan', run: startEdit })
    : nextView?.primaryAction === 'invoice'
      ? { label: 'Create invoice', run: () => next && void run('Creating invoice', () => api(`/api/milestones/${next.id}/draft`, { approver: 'You' }), 'Draft invoice created.') }
      : nextView?.primaryAction === 'send'
        ? { label: 'Send invoice', run: () => next && setSendTarget(next) }
        : nextView?.primaryAction === 'check'
          ? { label: 'Check with PayPal', run: () => next && void checkPaypal(next) }
          : null
  return (
    <div className="workbench">
      <a className="back-link" href="/" onClick={e => { e.preventDefault(); navigate('/') }}><ArrowLeft size={16} /> Portfolio</a>
      <p className="sr-only" aria-live="polite">{announcement}</p>

      <header className="workbench-head">
        <div>
          <h1>{project.client_name}</h1>
          <p className="muted">{project.client_email}</p>
        </div>
        <div className="workbench-figures">
          <span><span className="figure-label">Received</span><Money amountMinor={received} size="lg" tone={received > 0 ? 'paid' : 'muted'} /></span>
          <span>
            <span className="figure-label">Next due</span>
            {next ? <><Money amountMinor={toMinor(next.amount)} size="xl" /><span className="muted small">{formatDue(next.due_date)}</span></> : <span className="muted">Complete</span>}
          </span>
        </div>
      </header>

      <MoneyBar milestones={project.milestones} justPaid={justPaid} />

      <TrustChain project={project} />
      <TrustChainMobile project={project} />

      <div className="mobile-tabs" role="tablist" aria-label="Workbench views">
        <button role="tab" aria-selected={mobileTab === 'ledger'} onClick={() => setMobileTab('ledger')}>Ledger</button>
        <button role="tab" aria-selected={mobileTab === 'contract'} onClick={() => { setMobileTab('contract'); setPanelTab('contract') }}>Contract</button>
        <button role="tab" aria-selected={mobileTab === 'risk'} onClick={() => { setMobileTab('risk'); setPanelTab('risk') }}>Risk{project.risk ? ` (${project.risk.risks.length})` : ''}</button>
      </div>

      {project.status === 'BLOCKED' && (
        <div className="state-box state-error">
          <p>This plan is blocked by the fixed checks. Every amount and date must be justified by its evidence quote.</p>
        </div>
      )}

      <div className="workbench-grid" data-mobile={mobileTab}>
        <ContractSheet contract={project.source_text} milestones={project.milestones} risk={project.risk}
          activeId={activeId} traceId={traceId} tab={panelTab} onTabChange={setPanelTab}
          onSelect={setActiveId} onReviewRisk={reviewRisk} />
        <Ledger project={project} activeId={activeId} busy={busy} justPaid={justPaid}
          editing={editingPlan} draft={currentDraft} checks={checks}
          onSelect={setActiveId}
          onShowEvidence={id => { setActiveId(id); setTraceId(id) }}
          onApprove={() => { if (canApprove) void run('Approving plan', () => api(`/api/projects/${id}/approve`, { approver: 'You' }), 'Plan approved. Draft and send stay separate.') }}
          onEdit={startEdit}
          onCancelEdit={() => { setEditingPlan(false); setDraft(null) }}
          onSaveEdit={() => void savePlan()}
          onChangeDraft={patch => setDraft(d => d ? { ...d, ...patch } : d)}
          onReextract={() => navigate('/new')}
          onDraft={m => void run('Creating invoice', () => api(`/api/milestones/${m.id}/draft`, { approver: 'You' }), 'Draft invoice created.')}
          onSend={m => setSendTarget(m)}
          onCheck={m => void checkPaypal(m)}
          onViewRisk={() => { setPanelTab('risk'); setMobileTab('risk') }}
        />
      </div>

      {info?.mode === 'sample' && (
        <div className="demo-controls">
          <span className="muted small">Demo controls</span>
          {sentMilestone ? (
            <>
              <Button variant="quiet" loading={busy === 'Simulating payment'} onClick={() => void simulatePay(sentMilestone)}>
                Simulate client payment for milestone {sentMilestone.seq}
              </Button>
              <Button variant="quiet" onClick={() => void simulateForged(sentMilestone)}>Send forged webhook</Button>
            </>
          ) : (
            <Button variant="quiet" disabled disabledReason="Send an invoice to enable the simulated payment.">
              Simulate client payment
            </Button>
          )}
        </div>
      )}

      {mobileAction && (
        <div className="mobile-action">
          <Button variant="primary" loading={!!busy} onClick={mobileAction.run}>{mobileAction.label}</Button>
        </div>
      )}

      <Dialog open={!!sendTarget} title="Send this invoice?" confirmLabel="Send invoice"
        onCancel={() => setSendTarget(null)}
        onConfirm={() => {
          const target = sendTarget
          setSendTarget(null)
          if (target) void run('Sending invoice', () => api(`/api/milestones/${target.id}/send`, { approver: 'You', confirm: true }), 'Invoice sent. Open the payer link in the ledger. No PayPal email was sent.')
        }}>
        {sendTarget && <p>Send <strong>{sendTarget.title}</strong> for <Money amountMinor={toMinor(sendTarget.amount)} size="sm" />? PayPal will not email anyone.</p>}
      </Dialog>
    </div>
  )
}
