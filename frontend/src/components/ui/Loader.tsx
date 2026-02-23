/**
 * Loader — spinner component for loading states.
 */

export interface LoaderProps {
  size?: 'sm' | 'md' | 'lg';
  fullScreen?: boolean;
  label?: string;
  className?: string;
}

export function Loader({
  size = 'md',
  fullScreen = false,
  label,
  className = '',
}: LoaderProps) {
  const spinner = (
    <div
      className={`loader loader--${size} ${className}`}
      role="status"
      aria-label={label ?? 'Loading'}
    >
      <div className="loader__spinner" />
      {label && <span className="loader__label">{label}</span>}
    </div>
  );

  if (fullScreen) {
    return <div className="loader__fullscreen">{spinner}</div>;
  }

  return spinner;
}
