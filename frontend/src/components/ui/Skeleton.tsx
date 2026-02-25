/**
 * Skeleton — animated placeholder blocks for content that is loading.
 *
 * Variants:
 *   - "text"   → single line placeholder (default)
 *   - "rect"   → rectangular card/image placeholder
 *   - "circle" → circular avatar placeholder
 *
 * Usage:
 *   <Skeleton />                           // default text line
 *   <Skeleton variant="rect" height={120} />
 *   <Skeleton variant="circle" width={48} height={48} />
 *   <Skeleton count={3} />                 // 3 text lines
 */

import styles from "./Skeleton.module.css";

export interface SkeletonProps {
  variant?: "text" | "rect" | "circle";
  /** Width in px or CSS string. Defaults to "100%" for text/rect. */
  width?: number | string;
  /** Height in px or CSS string. Defaults based on variant. */
  height?: number | string;
  /** Render multiple skeleton lines (only for "text" variant). */
  count?: number;
  /** Additional class. */
  className?: string;
}

const DEFAULT_HEIGHT: Record<string, string> = {
  text: "1em",
  rect: "120px",
  circle: "48px",
};

export default function Skeleton({
  variant = "text",
  width,
  height,
  count = 1,
  className,
}: SkeletonProps) {
  const resolvedHeight =
    typeof height === "number" ? `${height}px` : height ?? DEFAULT_HEIGHT[variant];
  const resolvedWidth =
    typeof width === "number"
      ? `${width}px`
      : width ?? (variant === "circle" ? resolvedHeight : "100%");

  const baseStyle: React.CSSProperties = {
    width: resolvedWidth,
    height: resolvedHeight,
  };

  const variantClass =
    variant === "circle" ? styles.circle : variant === "rect" ? styles.rect : styles.text;

  if (count > 1 && variant === "text") {
    return (
      <div className={`${styles.stack} ${className ?? ""}`.trim()}>
        {Array.from({ length: count }, (_, i) => (
          <div
            key={i}
            className={`${styles.bone} ${variantClass}`}
            style={{
              ...baseStyle,
              // Last line is shorter for visual realism
              width: i === count - 1 ? "60%" : resolvedWidth,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`${styles.bone} ${variantClass} ${className ?? ""}`.trim()}
      style={baseStyle}
    />
  );
}
