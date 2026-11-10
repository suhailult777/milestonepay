import { useEffect, useRef, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { api } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { Skeleton } from '../../components/ui/Skeleton'
import { navigate } from '../../lib/router'
import type { Info } from '../../types'

type Stage = 'empty' | 'proposing' | 'failed' | 'proposed'

export function NewContractPage({ info }: { info: Info | null }) {
  const [typed, setTyped] = useState<string | null>(null)
  const text = typed ?? (info?.mode === 'sample' ? info.sample_contract : '')
  const [stage, setStage] = useState<Stage>('empty')
  const [errors, setErrors] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (stage !== 'proposing') return
    const started = Date.now()
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 500)
    return () => window.clearInterval(timer)
  }, [stage])

  const propose = async () => {
    if (!text.trim()) {
      setStage('failed')
      setErrors(['Paste the contract text first.'])
      return
    }
    if (new URLSearchParams(location.search).get('fixture') === 'fail') {
      setStage('failed')
      setErrors(['Fixture failure requested. No project was created.'])
      return
    }
    setStage('proposing')
    setElapsed(0)
    setErrors([])
    setMessage('')
    try {
      const r = await api<{ project_id: string; status: string; errors: string[] }>('/api/projects', { text })
      if (r.errors.length) {
        setStage('failed')
        setErrors(r.errors)
        setMessage(`Project ${r.project_id} was saved as Blocked. Open it to fix the plan.`)
      } else {
        setStage('proposed')
        navigate(`/p/${r.project_id}`)
      }
    } catch (e) {
      setStage('failed')
      setErrors([e instanceof Error ? e.message : String(e)])
    }
  }

  return (
    <div className="new-page">
      <header className="new-head">
        <h1>Add a contract</h1>
        <p className="muted">The model proposes. You review every amount and date before anything is sent.</p>
      </header>
      <div className="new-grid">
        <section className="sheet new-form">
          <div className="ui-field">
            <div className="new-field-head">
              <label className="ui-field-label" htmlFor="contract-text">Contract text</label>
              {info?.mode === 'sample' && (
                <button type="button" className="text-link" onClick={() => setTyped(info.sample_contract ?? '')}>
                  Use the sample contract
                </button>
              )}
            </div>
            <textarea id="contract-text" ref={textareaRef} className="ui-input ui-textarea" value={text}
              onChange={e => setTyped(e.target.value)}
              placeholder="Paste the statement of work, fee schedule, or milestone terms." />
          </div>
          <div className="new-actions">
            <Button variant="primary" onClick={() => void propose()} loading={stage === 'proposing'}>
              <Sparkles size={16} /> Propose milestones
            </Button>
          </div>
        </section>

        <section className="sheet new-result" aria-live="polite">
          <h2>Proposed milestones</h2>
          {stage === 'empty' && (
            <>
              <div className="empty-ledger" aria-hidden="true">
                {[0, 1, 2].map(i => (
                  <div className="empty-row" key={i}>
                    <span className="empty-seq">{i + 1}</span>
                    <div className="empty-lines"><Skeleton width="58%" /><Skeleton width="36%" /></div>
                    <div className="empty-figure"><Skeleton width={72} height={20} /><Skeleton width={54} height={12} /></div>
                  </div>
                ))}
              </div>
              <p className="muted">Nothing yet. Paste the contract and choose Propose milestones. You review every amount and date before anything is sent.</p>
            </>
          )}
          {stage === 'proposing' && (
            <div className="proposing">
              <p>Proposing milestones. {elapsed}s</p>
              <Skeleton width="72%" /><Skeleton width="54%" /><Skeleton width="80%" />
              <p className="muted small">Model: {info?.labels.ai ?? 'checking provider'}.</p>
            </div>
          )}
          {stage === 'failed' && (
            <div className="state-box state-error" role="alert">
              <p>The model&apos;s output failed the checks. Nothing was sent.</p>
              {errors.map(error => <p key={error} className="small">{error}</p>)}
              {message && <p className="small">{message}</p>}
              <div className="state-actions">
                <Button onClick={() => void propose()}>Propose again</Button>
                <Button variant="secondary" onClick={() => { setStage('empty'); textareaRef.current?.focus() }}>Edit text</Button>
              </div>
            </div>
          )}
          {stage === 'proposed' && <p>Opening the workbench...</p>}
        </section>
      </div>
    </div>
  )
}
