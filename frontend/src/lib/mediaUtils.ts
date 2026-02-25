/**
 * Media URL utilities.
 *
 * Shared by ImageRenderer, MediaViewer, and any future media-rendering components.
 */

const API_ORIGIN = (() => {
  const base = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (!base) return "";
  try {
    return new URL(base).origin; // e.g. "http://localhost:8000"
  } catch {
    return "";
  }
})();

/**
 * Resolve a potentially relative Django media path to an absolute URL.
 *
 * - Already-absolute URLs (http/https) are returned unchanged.
 * - Relative paths like "/media/uploads/photo.jpg" are prefixed with
 *   the API origin extracted from VITE_API_BASE_URL.
 */
export function resolveMediaUrl(rawUrl: string): string {
  if (!rawUrl) return "";
  if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) {
    return rawUrl;
  }
  return `${API_ORIGIN}${rawUrl}`;
}
