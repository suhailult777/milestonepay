import { useEffect, useState } from 'react'

type Milestone = { id: string; seq: number; title: string; amount: string; currency: string; due_date: string;
  evidence: string; status: string; op_state: string; op_note: string | null; hold: string | null;
  invoice_id: string | null; pay_link: string | null; paid_amount: string | null }
type Audit = { actor: string; action: string; detail: Record<string, unknown>; at: number }
type Project = { id: string; client_name: string; client_email: string; total: string; status: string;
  extraction_source: string; milestones: Milestone[]; audit: Audit[] }
type Info = { mode: string; llm_provider: string; labels: { paypal: string; ai: string }; sample_contract: string }

async function api<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const j = await r.json()
  if (!r.ok) throw new Error(j.detail ?? r.statusText)
  return j as T
}

function lockedFor(m: Milestone, all: Milestone[]): Milestone | null {
  if (m.seq <= 1) return null
  const earlier = all.filter(x => x.seq < m.seq && x.status !== 'PAID')
  return earlier.length ? earlier[0] : null
}

export default function App() {
  const [info, setInfo] = useState<Info | null>(null)
  const [text, setText] = useState('')
  const [proj, setProj] = useState<Project | null>(null)
  const [errors, setErrors] = useState<string[]>([])
  const [ambig, setAmbig] = useState<string[]>([])
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState('')

  useEffect(() => {
    api<Info>('/api/info').then(async i => {
      setInfo(i); setText(i.sample_contract)
      const resume = new URLSearchParams(location.search).get('project')
      if (resume) setProj(await api<Project>(`/api/projects/${resume}`))
    }).catch(e => setMsg(String(e)))
  }, [])

  const refresh = async (id: string) => setProj(await api<Project>(`/api/projects/${id}`))
  const act = async (label: string, fn: () => Promise<unknown>) => {
    setMsg(''); setBusy(label)
    try { const r = await fn(); if (typeof r === 'string') setMsg(r); else if (r) setMsg(JSON.stringify(r)); if (proj) await refresh(proj.id) }
    catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
      if (proj) { try { await refresh(proj.id) } catch { /* keep the action error */ } }
    }
    finally { setBusy('') }
  }
  const extract = async () => {
    setErrors([]); setAmbig([]); setMsg(''); setBusy('Extracting. A local model can take 15 to 30 seconds.')
    try {
      const r = await api<{ project_id: string; errors: string[]; ambiguities: string[] }>('/api/projects', { text })
      setErrors(r.errors); setAmbig(r.ambiguities); await refresh(r.project_id)
    } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
    finally { setBusy('') }
  }
  const sim = info?.mode === 'sample'

  return <main>
    <header>
      <h1>MilestonePay</h1>
      <p className="muted">Evidence-first milestone invoices for freelancers paid in USD. The model proposes, fixed code checks, you approve, PayPal confirms before the next milestone unlocks.</p>
      {info && <p className="badges">
        <span className={`badge ${sim ? 'sim' : 'live'}`}>{info.labels.paypal}</span>{' '}
        <span className={`badge ${info.labels.ai.startsWith('Fixture') ? 'sim' : 'live'}`}>{info.labels.ai}</span>{' '}
        <span className="badge no-funds">No real funds</span>
      </p>}
      {info && <p className="muted small">{sim
        ? 'Sample mode: simulated PayPal and fixture AI. No keys, no network calls. Switch to live sandbox mode for real PayPal sandbox API calls.'
        : 'Live sandbox mode: real PayPal sandbox API calls with fake funds. Production is not supported.'}</p>}
    </header>

    <div className="card">
      <h3>1. Contract</h3>
      <textarea value={text} onChange={e => setText(e.target.value)} />
      <button onClick={extract} disabled={!!busy}>{busy ? 'Working…' : 'Extract plan'}</button>
      {busy && <p className="muted">{busy}</p>}
    </div>

    {proj && <div className="card">
      <h3>2. Proposed plan for {proj.client_name} <span className="muted">({proj.client_email})</span>, total USD {proj.total}</h3>
      <p>Plan status: <span className={`badge ${proj.status}`}>{proj.status}</span> · extracted by <span className="mono">{proj.extraction_source}</span></p>
      {errors.length > 0 && <div className="blocked">
        <b>Blocked by fixed checks. This plan cannot be approved.</b>
        {errors.map(e => <p key={e} className="err">{e}</p>)}
      </div>}
      {ambig.map(a => <p key={a} className="warn">Needs your attention: {a}</p>)}
      <button disabled={proj.status !== 'PROPOSED' || !!busy} onClick={() => act('Approving plan…', () => api(`/api/projects/${proj.id}/approve`, {}).then(() => 'Plan approved. Draft and send are separate steps.'))}>Approve plan</button>
      <p className="muted small">Approval is a human gate. The model cannot approve or send anything.</p>
    </div>}

    {proj?.milestones.map(m => {
      const lockedBy = lockedFor(m, proj.milestones)
      return <div className={`card milestone ${lockedBy ? 'is-locked' : ''}`} key={m.id}>
        <div className="row">
          <b>Milestone {m.seq}: {m.title}</b>
          <span className={`badge ${m.status}`}>{m.status}</span>
          {lockedBy && <span className="badge locked">LOCKED</span>}
        </div>
        <p>USD {m.amount} · due {m.due_date}</p>
        <blockquote>Evidence: “{m.evidence}”</blockquote>
        {lockedBy && <p className="warn">Locked until milestone {lockedBy.seq} is confirmed PAID by PayPal.</p>}
        {m.invoice_id && <p className="mono">Invoice {m.invoice_id}{m.paid_amount ? ` · paid ${m.paid_amount}` : ''}</p>}
        {m.pay_link && <p className="mono">Payer link: <a href={m.pay_link} target="_blank" rel="noreferrer">{m.pay_link}</a></p>}
        {m.hold && <p className="err">On hold: {m.hold}</p>}
        {m.op_state === 'RECONCILIATION_REQUIRED' || m.op_state === 'IN_FLIGHT'
          ? <p className="err">PayPal outcome unknown ({m.op_state}). Automatic retry is blocked. Reconcile by the exact invoice number before any retry.
              <button onClick={() => act('Reconciling with PayPal…', () => api<{ recovered_invoice_id?: string; note?: string; error?: string }>(`/api/milestones/${m.id}/reconcile`, {}).then(r => r.recovered_invoice_id ? `Recovered the existing invoice: ${r.recovered_invoice_id}` : (r.note || r.error || 'Reconciliation finished.')))}>Reconcile with PayPal</button></p>
          : null}
        <div className="buttons">
          <button disabled={proj.status !== 'APPROVED' || !!m.invoice_id || !!busy || !!lockedBy}
            onClick={() => act('Creating draft invoice…', () => api<{ invoice_id: string }>(`/api/milestones/${m.id}/draft`, {}).then(r => `Draft invoice ready: ${r.invoice_id}`))}>Create draft invoice</button>
          {sim && proj.status === 'APPROVED' && !m.invoice_id && m.op_state === 'NONE' && !lockedBy && <button disabled={!!busy}
            onClick={() => act('Arming timeout…', () => api<{ armed: boolean }>(`/api/simulate/timeout/${m.id}`, {}).then(() => 'Create timeout armed. Now click Create draft invoice, then Reconcile.'))}>Arm create timeout (sample)</button>}
          <button disabled={m.status !== 'DRAFTED' || !!busy}
            onClick={() => { if (confirm(`Send invoice for USD ${m.amount}?`)) act('Sending invoice…', () => api(`/api/milestones/${m.id}/send`, { confirm: true }).then(() => 'Invoice marked SENT. Payer link shown below. No PayPal email was sent.')) }}>Send invoice…</button>
          <button disabled={!m.invoice_id || !!busy}
            onClick={() => act('Checking PayPal…', () => api<{ outcome: string }>(`/api/milestones/${m.id}/refresh`, {}).then(r => {
              if (r.outcome === 'milestone_paid') return 'PayPal confirms PAID. Merchant, USD, and exact amount all match.'
              if (r.outcome === 'milestone_sent') return 'PayPal still shows UNPAID. The invoice remains SENT.'
              if (r.outcome === 'milestone_mismatch') return 'PayPal returned a mismatch. This milestone is not PAID.'
              return `PayPal result: ${r.outcome}`
            }))}>Check PayPal status</button>
        </div>
        {sim && m.status === 'SENT' && <div className="buttons">
          <button onClick={() => act('Simulating payment…', () => api<{ outcome: string }>(`/api/simulate/pay/${m.id}`, {}).then(r => r.outcome === 'milestone_paid' ? 'Simulated payment accepted. Milestone is PAID.' : `Simulated result: ${r.outcome}`))}>Simulate client payment (sample)</button>
          <button onClick={() => act('Sending forged webhook…', () => api<{ outcome: string }>(`/api/simulate/forged/${m.id}`, {}).then(r => r.outcome === 'rejected' ? 'Forged webhook rejected. No state change.' : `Forged result: ${r.outcome}`))}>Send forged webhook (sample)</button>
        </div>}
      </div>
    })}

    {msg && <p className="mono result">Result: {msg}</p>}

    {proj && <div className="card"><h3>Audit trail</h3>
      {proj.audit.map((a, i) => <div key={i} className="mono audit">{new Date(a.at * 1000).toLocaleTimeString()} · {a.actor} · {a.action} · {JSON.stringify(a.detail)}</div>)}
    </div>}
  </main>
}
