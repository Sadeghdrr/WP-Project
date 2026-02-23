/**
 * Skeleton — loading placeholder with shimmer animation.
 */
import type { CSSProperties } from 'react';

export interface SkeletonProps {
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
  count?: number;
  className?: string;
}

export function Skeleton({
  variant = 'text',
  width,
  height,
  count = 1,
  className = '',
}: SkeletonProps) {
  const style: CSSProperties = {
    width:
      width ??
      (variant === 'circular' ? (height ?? 40) : '100%'),
    height:
      height ??
      (variant === 'text'
        ? '1em'
        : variant === 'circular'
          ? (width ?? 40)
          : 120),
    borderRadius:
      variant === 'circular' ? '50%' : variant === 'text' ? '4px' : '8px',
  };

  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`skeleton skeleton--${variant} ${className}`}
          style={style}
          aria-hidden="true"
        />
      ))}
    </>
  );
}
