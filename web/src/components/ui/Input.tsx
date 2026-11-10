import { useId, type InputHTMLAttributes } from 'react'

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  error?: string
  hint?: string
}

export function Input({ label, error, hint, id, className = '', ...rest }: Props) {
  const generated = useId()
  const inputId = id ?? generated
  const helpId = `${inputId}-help`
  return (
    <label className={`ui-field ${className}`.trim()} htmlFor={inputId}>
      <span className="ui-field-label">{label}</span>
      <input {...rest} id={inputId} className="ui-input" aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? helpId : undefined} />
      {(error || hint) && <span id={helpId} className={error ? 'ui-field-error' : 'ui-field-hint'}>{error ?? hint}</span>}
    </label>
  )
}
