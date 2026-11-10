import { useEffect, useMemo, useRef, useState } from 'react'
import { findEvidenceSpans } from '../../lib/evidence'
import { RiskReviewPanel } from './RiskReview'
import type { Milestone, RiskNote, RiskReview } from '../../types'

type Segment = { text: string; milestone?: Milestone; risk?: RiskNote }

function renderText(text: string) {
  return text.split(/(\d{4}-\d{2}-\d{2})/g).map((part, i) => (
    /^\d{4}-\d{2}-\d{2}$/.test(part)
      ? <span key={i} className="text-nowrap">{part}</span>
      : <span key={i}>{part}</span>
  ))
}

export function ContractSheet({ contract, milestones, risk, activeId, traceId, tab, onTabChange, onSelect, onReviewRisk }:
  {
    contract: string
    milestones: Milestone[]
    risk: RiskReview | null
    activeId: string | null
    traceId: string | null
    tab: 'contract' | 'risk'
    onTabChange: (tab: 'contract' | 'risk') => void
    onSelect: (id: string) => void
    onReviewRisk: () => void
  }) {
  const ref = useRef<HTMLDivElement>(null)
  const [riskTrace, setRiskTrace] = useState<string | null>(null)

  const segments = useMemo(() => {
    const annotations: { start: number; end: number; milestone?: Milestone; risk?: RiskNote }[] = []
    for (const m of milestones) {
      const span = findEvidenceSpans(contract, m.evidence)[0]
      if (span) annotations.push({ ...span, milestone: m })
    }
    for (const note of risk?.risks ?? []) {
      const span = findEvidenceSpans(contract, note.evidence)[0]
      if (span) annotations.push({ ...span, risk: note })
    }
    annotations.sort((a, b) => a.start - b.start)
    const points = Array.from(new Set([0, ...annotations.flatMap(a => [a.start, a.end]), contract.length])).sort((a, b) => a - b)
    const out: Segment[] = []
    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i]
      const end = points[i + 1]
      if (start >= end) continue
      const active = annotations.filter(a => a.start <= start && a.end >= end)
      out.push({
        text: contract.slice(start, end),
        milestone: active.find(a => a.milestone)?.milestone,
        risk: active.find(a => a.risk)?.risk,
      })
    }
    return out
  }, [contract, milestones, risk])

  useEffect(() => {
    if (!traceId) return
    ref.current?.querySelector<HTMLElement>(`[data-milestone="${traceId}"]`)?.scrollIntoView({ block: 'center', behavior: 'auto' })
  }, [traceId])

  useEffect(() => {
    if (!riskTrace) return
    ref.current?.querySelector<HTMLElement>('.risk-mark, .has-risk')?.scrollIntoView({ block: 'center', behavior: 'auto' })
  }, [riskTrace])

  return (
    <section className="contract-sheet" aria-label="Contract">
      <div className="contract-head">
        <div className="contract-tabs" role="tablist" aria-label="Contract views">
          <button role="tab" aria-selected={tab === 'contract'} onClick={() => onTabChange('contract')}>Contract</button>
          <button role="tab" aria-selected={tab === 'risk'} onClick={() => onTabChange('risk')}>
            Risk review{risk ? ` (${risk.risks.length})` : ''}
          </button>
        </div>
        {tab === 'contract' && <span className="muted small">Select a highlighted sentence to connect it to the ledger.</span>}
      </div>

      {tab === 'contract' ? (
        !contract.trim() ? <p className="state-box">Paste the contract text to start.</p> : (
          <div className="contract-text" ref={ref}>
            {segments.map((segment, i) => segment.milestone ? (
              <mark key={i} className={`contract-mark ${activeId === segment.milestone.id ? 'is-active' : ''} ${segment.risk ? 'has-risk' : ''}`}
                data-milestone={segment.milestone.id} tabIndex={0}
                title={`Evidence for milestone ${segment.milestone.seq}`}
                onClick={() => onSelect(segment.milestone!.id)}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(segment.milestone!.id) }
                }}>
                {renderText(segment.text)}
              </mark>
            ) : segment.risk ? (
              <span key={i} className="risk-mark" title={segment.risk.title}>{renderText(segment.text)}</span>
            ) : <span key={i}>{renderText(segment.text)}</span>)}
          </div>
        )
      ) : (
        <RiskReviewPanel risk={risk} onRun={onReviewRisk} onShowInText={quote => { onTabChange('contract'); setRiskTrace(quote) }} />
      )}
    </section>
  )
}
