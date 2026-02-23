/**
 * useDelayedLoading — prevents flash-of-loading-state.
 *
 * Problem:
 *   When data loads in <100ms, showing a skeleton for a single frame
 *   creates a distracting flash. But if we never show loading, slow
 *   connections appear broken.
 *
 * Solution:
 *   Delay showing the loading indicator by a threshold (default 150ms).
 *   If data arrives before the threshold, the user never sees the skeleton.
 *   If data takes longer, the skeleton appears smoothly.
 *
 * Usage:
 *   const { data, isLoading } = useQuery({ ... });
 *   const showSkeleton = useDelayedLoading(isLoading);
 *
 *   if (showSkeleton) return <TableSkeleton />;
 *   if (data) return <Table data={data} />;
 */
import { useState, useEffect, useRef } from 'react';

/**
 * @param isLoading  Whether the underlying query is loading
 * @param delay      Minimum ms before showing loading UI (default 150)
 * @param minDisplay Minimum ms to show loading once visible (default 300)
 *                   Prevents skeleton from appearing for only 1 frame
 */
export function useDelayedLoading(
  isLoading: boolean,
  delay = 150,
  minDisplay = 300,
): boolean {
  const [showLoading, setShowLoading] = useState(false);
  const showTimeRef = useRef<number>(0);

  useEffect(() => {
    if (isLoading) {
      // Start delay timer before showing loading
      const timer = setTimeout(() => {
        setShowLoading(true);
        showTimeRef.current = Date.now();
      }, delay);

      return () => clearTimeout(timer);
    }

    // When loading finishes, ensure minimum display time
    if (showLoading) {
      const elapsed = Date.now() - showTimeRef.current;
      const remaining = Math.max(0, minDisplay - elapsed);

      if (remaining > 0) {
        const timer = setTimeout(() => setShowLoading(false), remaining);
        return () => clearTimeout(timer);
      }
      setShowLoading(false);
    }

    return undefined;
  }, [isLoading, delay, minDisplay, showLoading]);

  return showLoading;
}
