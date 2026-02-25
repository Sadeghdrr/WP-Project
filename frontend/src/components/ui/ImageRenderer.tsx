/**
 * ImageRenderer
 *
 * Universal, reusable image component for the application.
 *
 * Two loading strategies controlled by `requiresAuth`:
 *
 *   requiresAuth=false (default)
 *     Resolves the backend URL to the API origin and uses a plain <img>.
 *     The browser handles caching natively. No extra fetch, no blob dance.
 *     Suitable for public media endpoints (e.g. suspect profile photos).
 *
 *   requiresAuth=true
 *     Fetches the image via the JWT-authenticated channel
 *     (fetch + Authorization header → Blob → objectURL).
 *     Uses AbortController so the in-flight request is actually cancelled
 *     when the component unmounts — this eliminates the double-network-request
 *     that React StrictMode (dev-only) otherwise causes.
 *
 * Preview mode (default: true)
 *     Renders a clickable thumbnail. Clicking opens a fullscreen lightbox.
 *     No <a href> is used, so there is no page navigation.
 *
 * URL resolution
 *     Django media paths are relative (e.g. "/media/uploads/photo.jpg").
 *     This component prepends VITE_API_BASE_URL's origin so the request
 *     reaches the backend, not the Vite dev server.
 */

import { useState, useEffect, useCallback, type CSSProperties } from "react";
import { getAccessToken } from "../../api/client";
import { resolveMediaUrl } from "../../lib/mediaUtils";
import css from "./ImageRenderer.module.css";

// ---------------------------------------------------------------------------
// Authenticated blob URL hook (requiresAuth=true path)
// ---------------------------------------------------------------------------

interface BlobState {
  url: string | null;
  loading: boolean;
  error: string | null;
}

/**
 * Fetches an image through the JWT channel and returns a temporary blob:
 * object URL. Uses AbortController so that when the component unmounts
 * (including the intentional StrictMode unmount in development) the in-flight
 * HTTP request is actually cancelled — preventing the double-request that is
 * otherwise visible in the browser Network tab.
 *
 * The returned blob URL is revoked on cleanup to avoid memory leaks.
 */
function useAuthBlobUrl(rawUrl: string): BlobState {
  // Derived-state reset: when rawUrl changes, update synchronously during
  // render (React-recommended alternative to useEffect resets). This avoids
  // synchronous setState calls inside effect bodies (react-hooks lint rules).
  const [prevUrl, setPrevUrl] = useState(rawUrl);
  const [state, setState] = useState<BlobState>({
    url: null,
    loading: !!rawUrl,
    error: null,
  });
  if (prevUrl !== rawUrl) {
    setPrevUrl(rawUrl);
    setState({ url: null, loading: !!rawUrl, error: null });
  }

  useEffect(() => {
    if (!rawUrl) return; // nothing to load; state is already reset above

    const controller = new AbortController();
    let objectUrl: string | null = null;

    async function load() {
      const resolved = resolveMediaUrl(rawUrl);
      const token = getAccessToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      try {
        const res = await fetch(resolved, {
          headers,
          signal: controller.signal, // ← key: ties the request to this effect
        });

        if (!res.ok) {
          setState({ url: null, loading: false, error: `HTTP ${res.status}` });
          return;
        }

        const blob = await res.blob();
        objectUrl = URL.createObjectURL(blob);
        setState({ url: objectUrl, loading: false, error: null });
      } catch (e) {
        // AbortError is expected on unmount — not a real error
        if (e instanceof DOMException && e.name === "AbortError") return;
        setState({
          url: null,
          loading: false,
          error: e instanceof Error ? e.message : "Network error",
        });
      }
    }

    void load();

    return () => {
      controller.abort(); // cancels the in-flight HTTP request immediately
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [rawUrl]);

  return state;
}

// ---------------------------------------------------------------------------
// Direct-mode image state
// ---------------------------------------------------------------------------

interface DirectState {
  loaded: boolean;
  error: boolean;
}

// ---------------------------------------------------------------------------
// Lightbox portal
// ---------------------------------------------------------------------------

function Lightbox({
  src,
  alt,
  caption,
  onClose,
}: {
  src: string;
  alt: string;
  caption?: string;
  onClose: () => void;
}) {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).dataset.backdrop) onClose();
    },
    [onClose],
  );

  return (
    <div
      className={css.backdrop}
      data-backdrop="1"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label="Image lightbox"
      tabIndex={-1}
    >
      <div className={css.lightbox}>
        <button
          type="button"
          className={css.closeBtn}
          onClick={onClose}
          aria-label="Close lightbox"
        >
          ✕
        </button>
        <img
          src={src}
          alt={alt}
          className={css.lightboxImg}
        />
        {caption && <p className={css.caption}>{caption}</p>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ImageRendererProps {
  /** Raw URL or path from the backend (may be relative like /media/…). */
  src: string | null | undefined;
  /** Alt text for accessibility. */
  alt?: string;
  /**
   * When true, renders a clickable thumbnail that opens a fullscreen
   * lightbox. When false, renders the image inline. Default: true.
   */
  preview?: boolean;
  /**
   * When true, fetches the image via fetch() with a JWT Authorization
   * header and renders a blob URL. Fixes the double-request from React
   * StrictMode via AbortController.
   * When false (default), uses a plain <img src={resolvedUrl}> — no extra
   * fetch, browser caching works normally.
   */
  requiresAuth?: boolean;
  /** Optional caption shown beneath the lightbox image. */
  caption?: string;
  /** CSS class applied to the thumbnail container / inline wrapper. */
  className?: string;
  /** Inline styles applied to the thumbnail container / inline wrapper. */
  style?: CSSProperties;
  /** Icon shown when src is empty. Defaults to "👤". */
  placeholderIcon?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImageRenderer({
  src,
  alt = "Image",
  preview = true,
  requiresAuth = false,
  caption,
  className,
  style,
  placeholderIcon = "👤",
}: ImageRendererProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false);

  // ── Authenticated blob mode ─────────────────────────────────
  const blob = useAuthBlobUrl(src && requiresAuth ? src : "");

  // ── Direct img mode ─────────────────────────────────────────
  const resolvedDirect = src && !requiresAuth ? resolveMediaUrl(src) : "";

  // Derived-state reset for direct mode: when resolvedDirect changes, reset
  // synchronously during the render phase instead of via useEffect.
  const [prevDirectSrc, setPrevDirectSrc] = useState(resolvedDirect);
  const [directState, setDirectState] = useState<DirectState>({ loaded: false, error: false });
  if (prevDirectSrc !== resolvedDirect) {
    setPrevDirectSrc(resolvedDirect);
    setDirectState({ loaded: false, error: false });
  }

  const handleOpenLightbox = useCallback(() => setLightboxOpen(true), []);
  const handleCloseLightbox = useCallback(() => setLightboxOpen(false), []);

  // Resolve the display URL for the lightbox and <img> in non-auth mode
  const displaySrc = requiresAuth ? (blob.url ?? "") : resolvedDirect;
  const isReady = requiresAuth ? blob.url !== null : directState.loaded;
  const hasError = requiresAuth ? blob.error !== null : directState.error;
  const isLoading = requiresAuth ? blob.loading : !directState.loaded && !directState.error && !!src;

  // ── No-preview (inline) mode ────────────────────────────────
  if (!preview) {
    if (!src) {
      return (
        <span className={className} style={style} aria-label={placeholderIcon}>
          {placeholderIcon}
        </span>
      );
    }

    if (requiresAuth) {
      if (blob.loading) return <div className={`${css.loading} ${className ?? ""}`} style={style} aria-label="Loading image…" />;
      if (blob.error || !blob.url) return <span style={style}>{placeholderIcon}</span>;
      return <img src={blob.url} alt={alt} className={`${css.inlineImg} ${className ?? ""}`} style={style} />;
    }

    return (
      <img
        src={resolvedDirect}
        alt={alt}
        className={`${css.inlineImg} ${className ?? ""}`}
        style={style}
        onLoad={() => setDirectState({ loaded: true, error: false })}
        onError={() => setDirectState({ loaded: false, error: true })}
      />
    );
  }

  // ── Preview (thumbnail + lightbox) mode ────────────────────
  return (
    <>
      <button
        type="button"
        className={`${css.thumbBtn} ${className ?? ""}`}
        style={style}
        onClick={handleOpenLightbox}
        disabled={!isReady}
        title={isReady ? "Click to enlarge" : undefined}
        aria-label={isReady ? (caption ?? alt) : "Loading image"}
      >
        {!src ? (
          <div className={css.placeholder} aria-hidden="true">{placeholderIcon}</div>
        ) : hasError ? (
          <div className={css.error} title={requiresAuth ? (blob.error ?? "Failed") : "Failed to load"}>
            ⚠️
          </div>
        ) : isLoading ? (
          <div className={css.loading} aria-label="Loading…" />
        ) : requiresAuth ? (
          <img src={blob.url!} alt={alt} className={css.thumb} />
        ) : (
          <img
            src={resolvedDirect}
            alt={alt}
            className={css.thumb}
            onLoad={() => setDirectState({ loaded: true, error: false })}
            onError={() => setDirectState({ loaded: false, error: true })}
          />
        )}
      </button>

      {lightboxOpen && displaySrc && (
        <Lightbox
          src={displaySrc}
          alt={alt}
          caption={caption}
          onClose={handleCloseLightbox}
        />
      )}
    </>
  );
}
