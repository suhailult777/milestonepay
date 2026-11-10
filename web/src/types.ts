export type Milestone = {
  id: string
  seq: number
  title: string
  amount: string
  currency: string
  due_date: string
  evidence: string
  status: string
  op_state: string
  op_note: string | null
  hold: string | null
  invoice_id: string | null
  pay_link: string | null
  paid_amount: string | null
}

export type Audit = {
  actor: string
  action: string
  detail: Record<string, unknown>
  at: number
}

export type RiskNote = {
  title: string
  severity: string
  evidence: string
  why: string
  question: string
}

export type RiskReview = {
  risks: RiskNote[]
  summary: string
}

export type PlanDraft = {
  client_name: string
  client_email: string
  total: string
  currency: string
  milestones: { id: string; title: string; amount: string; due_date: string; evidence: string }[]
}

export type BriefAction = {
  project_id: string
  client_name: string
  action: string
  amount: string
  due_date: string | null
  overdue: boolean
}

export type PortfolioBrief = {
  generated_at: number
  project_count: number
  currency: string
  outstanding_total: string
  collected_total: string
  overdue_count: number
  summary: string
  actions: BriefAction[]
}

export type Project = {
  id: string
  client_name: string
  client_email: string
  total: string
  currency: string
  source_text: string
  status: string
  extraction_source: string
  risk: RiskReview | null
  milestones: Milestone[]
  audit: Audit[]
}

export type ProjectSummary = {
  id: string
  client_name: string
  total: string
  currency: string
  status: string
  paid_total: string
  paid_count: number
  milestone_count: number
  next_due: string | null
  needs_action: string
}

export type Info = {
  mode: string
  llm_provider: string
  labels: { paypal: string; ai: string }
  sample_contract: string
}
