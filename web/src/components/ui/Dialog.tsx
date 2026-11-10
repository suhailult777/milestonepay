import { useEffect, useRef, type ReactNode } from 'react'
import { Button } from './Button'

export function Dialog({ open, title, children, confirmLabel = 'Confirm', onCancel, onConfirm }:
  { open: boolean; title: string; children: ReactNode; confirmLabel?: string; onCancel: () => void; onConfirm: () => void }) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onCancel])
  if (!open) return null
  return (
    <div className="dialog-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onCancel() }}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <h2 id="dialog-title">{title}</h2>
        <div className="dialog-body">{children}</div>
        <div className="dialog-actions">
          <button ref={cancelRef} type="button" className="ui-button ui-button-secondary" onClick={onCancel}>Cancel</button>
          <Button variant="primary" onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  )
}
