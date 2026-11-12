import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Ledger } from './Ledger'
import type { Milestone, Project } from '../../types'

function milestone(status: string, payLink: string | null = 'https://sandbox.paypal.test/invoice/1'): Milestone {
  return {
    id: 'm1',
    seq: 1,
    title: 'Design mockups',
    amount: '400.00',
    currency: 'USD',
    due_date: '2026-12-01',
    evidence: 'Milestone 1: Design mockups, USD 400, due 2026-12-01.',
    status,
    op_state: 'DONE',
    op_note: null,
    hold: null,
    invoice_id: 'INV-1',
    pay_link: payLink,
    paid_amount: status === 'PAID' ? '400.00' : null,
  }
}

function project(milestones: Milestone[]): Project {
  return {
    id: 'p1',
    client_name: 'Acme Labs',
    client_email: 'billing@acme-labs.example',
    total: '400.00',
    currency: 'USD',
    source_text: 'Milestone 1: Design mockups, USD 400, due 2026-12-01.',
    status: 'APPROVED',
    extraction_source: 'fixture',
    risk: null,
    milestones,
    audit: [],
  }
}

function renderLedger(m: Milestone) {
  return render(
    <Ledger
      project={project([m])}
      activeId={m.id}
      busy=""
      editing={false}
      draft={null}
      checks={[]}
      onSelect={() => {}}
      onShowEvidence={() => {}}
      onApprove={() => {}}
      onEdit={() => {}}
      onCancelEdit={() => {}}
      onSaveEdit={() => {}}
      onChangeDraft={() => {}}
      onReextract={() => {}}
      onDraft={() => {}}
      onSend={() => {}}
      onCheck={() => {}}
      onViewRisk={() => {}}
    />,
  )
}

describe('Ledger payer link', () => {
  it.each([
    ['SENT', true],
    ['PAID', true],
    ['PARTIAL', true],
    ['MISMATCH', true],
    ['DRAFTED', false],
    ['PLANNED', false],
  ])('renders the payer link for %s only when the invoice is past draft', (status, visible) => {
    renderLedger(milestone(status))
    const link = screen.queryByRole('link', { name: 'Open payer link' })
    if (visible) {
      expect(link?.getAttribute('href')).toBe('https://sandbox.paypal.test/invoice/1')
    } else {
      expect(link).toBeNull()
    }
  })

  it('does not render the payer link on a locked row', () => {
    renderLedger({ ...milestone('PLANNED'), hold: 'milestone 1 became REFUNDED' })
    expect(screen.queryByRole('link', { name: 'Open payer link' })).toBeNull()
  })
})
