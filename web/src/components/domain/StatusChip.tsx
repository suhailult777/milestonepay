import { CircleAlert, CircleCheck, ClockAlert, Flag, Lock, PencilLine, Quote, Send, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type ChipState =
  | 'paid' | 'sent' | 'overdue' | 'draft' | 'locked' | 'proposed'
  | 'risk-low' | 'risk-medium' | 'risk-high' | 'verified' | 'failed'

const MAP: Record<ChipState, { label: string; tone: string; Icon: LucideIcon }> = {
  paid: { label: 'Paid', tone: 'paid', Icon: CircleCheck },
  sent: { label: 'Sent', tone: 'sent', Icon: Send },
  overdue: { label: 'Overdue', tone: 'danger', Icon: ClockAlert },
  draft: { label: 'Draft', tone: 'lock', Icon: PencilLine },
  locked: { label: 'Locked', tone: 'lock', Icon: Lock },
  proposed: { label: 'Proposed', tone: 'ink', Icon: Sparkles },
  'risk-low': { label: 'Low risk', tone: 'lock', Icon: Flag },
  'risk-medium': { label: 'Medium risk', tone: 'warn', Icon: Flag },
  'risk-high': { label: 'High risk', tone: 'danger', Icon: Flag },
  verified: { label: 'Verbatim match', tone: 'paid', Icon: Quote },
  failed: { label: 'Not found in contract', tone: 'danger', Icon: CircleAlert },
}

export function StatusChip({ state, label }: { state: ChipState; label?: string }) {
  const { label: defaultLabel, tone, Icon } = MAP[state]
  return (
    <span className={`ui-chip ui-chip-${tone} ui-chip-${state}`}>
      <Icon size={14} aria-hidden="true" />
      <span>{label ?? defaultLabel}</span>
    </span>
  )
}
