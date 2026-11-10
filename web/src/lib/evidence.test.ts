import { describe, expect, it } from 'vitest'
import { findEvidenceSpans } from './evidence'

describe('findEvidenceSpans', () => {
  it('returns the exact range for a known quote', () => {
    const contract = 'Alpha. Milestone 1: Design, USD 400, due 2026-11-20. Omega.'
    expect(findEvidenceSpans(contract, 'Milestone 1: Design, USD 400, due 2026-11-20.')).toEqual([
      { start: 7, end: 52 },
    ])
  })

  it('returns [] when the quote is absent', () => {
    expect(findEvidenceSpans('Alpha.', 'Not here.')).toEqual([])
  })

  it('returns the first match when the quote appears twice', () => {
    expect(findEvidenceSpans('x 400 y 400', '400')).toEqual([{ start: 2, end: 5 }])
  })
})
