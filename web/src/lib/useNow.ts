import { useState } from 'react'

/** One stable "now" per mounted view, so rendering stays deterministic. */
export function useNow(): Date {
  const [now] = useState(() => new Date())
  return now
}
