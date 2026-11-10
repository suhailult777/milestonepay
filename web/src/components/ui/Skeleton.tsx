export function Skeleton({ width = '100%', height = 14, className = '' }:
  { width?: string | number; height?: string | number; className?: string }) {
  return <span className={`ui-skeleton ${className}`.trim()} style={{ width, height }} aria-hidden="true" />
}
