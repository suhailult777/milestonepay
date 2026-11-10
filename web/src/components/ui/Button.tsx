import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { LoaderCircle } from 'lucide-react'

type Variant = 'primary' | 'secondary' | 'quiet'
type Common = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'disabled'> & {
  variant?: Variant
  loading?: boolean
  children: ReactNode
}
type Enabled = { disabled?: false; disabledReason?: never }
type Disabled = { disabled: true; disabledReason: string }

export function Button({ variant = 'secondary', loading = false, disabled, disabledReason, children, className = '', ...rest }:
  Common & (Enabled | Disabled)) {
  const isDisabled = Boolean(disabled) || loading
  return (
    <button
      {...rest}
      type={rest.type ?? 'button'}
      className={`ui-button ui-button-${variant} ${className}`.trim()}
      disabled={isDisabled}
      aria-disabled={isDisabled}
      aria-busy={loading || undefined}
      title={disabledReason}
    >
      {loading && <LoaderCircle className="ui-spin" size={16} aria-hidden="true" />}
      <span>{children}</span>
    </button>
  )
}
