import { describe, expect, it } from 'vitest'
import { formatMoney, sumMinor, toMinor } from './money'

describe('money', () => {
  it('formats integer minor units without float drift', () => {
    expect(formatMoney(150000)).toEqual({ num: '1,500.00', cur: 'USD' })
    expect(formatMoney(5)).toEqual({ num: '0.05', cur: 'USD' })
  })

  it('sums minor units exactly', () => {
    expect(sumMinor([{ amount: '0.10' }, { amount: '0.20' }])).toBe(30)
    expect(sumMinor([{ amount: '400.00' }, { amount: '700' }])).toBe(110000)
  })

  it('parses amounts with commas and one decimal', () => {
    expect(toMinor('1,500.00')).toBe(150000)
    expect(toMinor('1.5')).toBe(150)
  })

  it('rejects malformed amounts', () => {
    expect(() => toMinor('abc')).toThrow('Invalid money amount')
    expect(() => toMinor('1.234')).toThrow('Invalid money amount')
  })
})
