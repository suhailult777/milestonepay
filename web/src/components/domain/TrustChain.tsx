import { CircleAlert, CircleCheck, Clock, Landmark, ShieldCheck, Sparkles, UserRoundCheck } from 'lucide-react'
import { formatIst } from '../../lib/dates'
import type { Project } from '../../types'

function State({ children, kind }: { children: string; kind: 'done' | 'waiting' | 'failed' }) {
  const Icon = kind === 'done' ? CircleCheck : kind === 'failed' ? CircleAlert : Clock
  return <span className={`trust-state trust-${kind}`}><Icon size={14} /> {children}</span>
}

export function TrustChain({ project }: { project: Project }) {
  const total = project.milestones.length
  const paid = project.milestones.filter(m => m.status === 'PAID').length
  const approved = project.audit.find(a => a.action === 'approved_plan')
  const failed = project.status === 'BLOCKED'
  const nodes = [
    { icon: <Sparkles size={20} />, actor: 'Model', what: `${total} milestone${total === 1 ? '' : 's'}`, state: <State kind="done">Proposed</State>, note: 'Can propose. Cannot approve, send, or mark paid.' },
    { icon: <ShieldCheck size={20} />, actor: 'Code checks', what: failed ? 'Fixed checks found problems' : 'currency, sum, dates, quotes', state: <State kind={failed ? 'failed' : 'done'}>{failed ? 'Failed' : 'Passed'}</State>, note: 'Checks currency, sum, dates, and that each quote appears verbatim.' },
    { icon: <UserRoundCheck size={20} />, actor: 'You', what: approved ? formatIst(approved.at) : 'Waiting for you', state: <State kind={approved ? 'done' : 'waiting'}>{approved ? 'Approved' : 'Waiting'}</State>, note: 'Approve the plan and send each invoice, as separate clicks.' },
    { icon: <Landmark size={20} />, actor: 'PayPal', what: `${paid} of ${total} paid`, state: <State kind={paid ? 'done' : 'waiting'}>{paid ? 'Confirmed' : 'Waiting'}</State>, note: 'A fresh invoice GET must say PAID before the next milestone unlocks.' },
  ]
  return (
    <section className="trust-chain" aria-label="Trust boundary">
      {nodes.map(node => (
        <div className="trust-node" key={node.actor} title={node.note}>
          <div className="trust-node-head"><span className="trust-icon">{node.icon}</span><strong>{node.actor}</strong>{node.state}</div>
          <p>{node.what}</p>
        </div>
      ))}
      <p className="trust-footer">The model can&apos;t approve, send or mark anything paid. Fixed code checks its work. You approve. PayPal confirms.</p>
    </section>
  )
}

export function TrustChainMobile({ project }: { project: Project }) {
  const total = project.milestones.length
  const paid = project.milestones.filter(m => m.status === 'PAID').length
  const approved = project.audit.find(a => a.action === 'approved_plan')
  return (
    <details className="trust-mobile">
      <summary>Who can move money</summary>
      <div className="trust-mobile-body">
        <p><strong>Model</strong> proposes {total} milestones.</p>
        <p><strong>Code checks</strong> currency, sum, dates, and verbatim quotes.</p>
        <p><strong>You</strong> {approved ? `approved the plan on ${formatIst(approved.at)}.` : 'have not approved the plan yet.'}</p>
        <p><strong>PayPal</strong> has confirmed {paid} of {total} paid.</p>
        <p className="trust-mobile-foot">The model can&apos;t approve, send or mark anything paid. Fixed code checks its work. You approve. PayPal confirms.</p>
      </div>
    </details>
  )
}
