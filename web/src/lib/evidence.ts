export type Span = { start: number; end: number }

export function findEvidenceSpans(contract: string, quote: string): Span[] {
  if (!quote.trim()) return []
  const index = contract.toLowerCase().indexOf(quote.toLowerCase())
  return index < 0 ? [] : [{ start: index, end: index + quote.length }]
}
