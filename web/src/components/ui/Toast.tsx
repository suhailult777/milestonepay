import { CircleAlert, CircleCheck } from 'lucide-react'

export type Toast = { id: number; kind: 'ok' | 'err'; text: string }

export function ToastStack({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="toast-stack" aria-live="polite" aria-atomic="false">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.kind}`} role="status">
          {t.kind === 'ok' ? <CircleCheck size={16} /> : <CircleAlert size={16} />}
          <span>{t.text}</span>
          <button type="button" className="toast-close" onClick={() => onDismiss(t.id)} aria-label="Dismiss notification">×</button>
        </div>
      ))}
    </div>
  )
}
