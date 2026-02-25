/**
 * MediaViewer
 *
 * Renders a clickable thumbnail for an evidence file attachment.
 * For images: clicking opens an in-page modal lightbox — no navigation.
 * For other types: provides a download trigger that also appends the JWT.
 *
 * Auth-aware: all fetches include the Bearer token so Django can enforce
 * per-file permissions without causing 404 / 403 in <img src> tags (which
 * cannot carry an Authorization header).
 *
 * URL resolution: Django returns relative media paths (`/media/…`). When the
 * frontend runs on a different origin than the API (e.g. Vite dev server on
 * :5173 vs Django on :8000), we prepend VITE_API_BASE_URL's origin.
 */

import { useState, useEffect, useCallback } from "react";
import { getAccessToken } from "../../api/client";
import css from "./MediaViewer.module.css";

// ---------------------------------------------------------------------------
// URL helper
// ---------------------------------------------------------------------------

const API_ORIGIN = (() => {
  const base = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (!base) return ""; // same-origin
  try {
    return new URL(base).origin; // e.g. "http://localhost:8000"
  } catch {
    return "";
  }
})();

/** Resolve a potentially relative Django media path to an absolute URL. */
function resolveMediaUrl(rawUrl: string): string {
  if (!rawUrl) return "";
  if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) {
    return rawUrl; // already absolute
  }
  // Relative path like /media/uploads/image.jpg
  return `${API_ORIGIN}${rawUrl}`;
}

// ---------------------------------------------------------------------------
// Authenticated image hook
// ---------------------------------------------------------------------------

/**
 * Fetches an image through the JWT-authenticated channel and returns a
 * temporary blob: object URL. Revokes the blob URL on unmount.
 *
 * Returns `null` while loading or if an error occurs.
 */
function useAuthenticatedBlobUrl(rawUrl: string): {
  blobUrl: string | null;
  error: string | null;
} {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!rawUrl) return;

    let objectUrl: string | null = null;
    let cancelled = false;

    async function load() {
      const resolved = resolveMediaUrl(rawUrl);
      const token = getAccessToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      try {
        const res = await fetch(resolved, { headers });
        if (!res.ok) {
          setError(`Failed to load file (${res.status})`);
          return;
        }
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Network error");
      }
    }

    void load();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [rawUrl]);

  return { blobUrl, error };
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MediaViewerProps {
  /** Raw URL / path as returned by the backend. */
  fileUrl: string;
  fileType: "image" | "video" | "audio" | "document" | string;
  fileTypeDisplay?: string;
  caption?: string;
}

const FILE_ICONS: Record<string, string> = {
  image: "🖼️",
  video: "🎬",
  audio: "🎵",
  document: "📄",
};

// ---------------------------------------------------------------------------
// Image card (auth-aware thumbnail + lightbox)
// ---------------------------------------------------------------------------

function ImageCard({ fileUrl, caption }: { fileUrl: string; caption?: string }) {
  const { blobUrl, error } = useAuthenticatedBlobUrl(fileUrl);
  const [open, setOpen] = useState(false);

  const handleOpen = useCallback(() => {
    if (blobUrl) setOpen(true);
  }, [blobUrl]);

  const handleClose = useCallback((e: React.MouseEvent) => {
    // Close when clicking the backdrop, not the inner image
    if ((e.target as HTMLElement).dataset.backdrop) setOpen(false);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Escape") setOpen(false);
  }, []);

  return (
    <>
      {/* Thumbnail */}
      <button
        type="button"
        className={css.thumbBtn}
        onClick={handleOpen}
        title="Click to enlarge"
        aria-label={caption || "View image"}
        disabled={!blobUrl}
      >
        {blobUrl ? (
          <img src={blobUrl} alt={caption || "Evidence image"} className={css.thumb} />
        ) : error ? (
          <div className={css.thumbError} title={error}>
            ⚠️
          </div>
        ) : (
          <div className={css.thumbLoading} aria-label="Loading…" />
        )}
      </button>

      {/* Modal / lightbox */}
      {open && blobUrl && (
        <div
          className={css.backdrop}
          data-backdrop="1"
          onClick={handleClose}
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
              onClick={() => setOpen(false)}
              aria-label="Close"
            >
              ✕
            </button>
            <img
              src={blobUrl}
              alt={caption || "Evidence image enlarged"}
              className={css.lightboxImg}
            />
            {caption && <p className={css.lightboxCaption}>{caption}</p>}
          </div>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Non-image card (download via fetch → blob to avoid navigation)
// ---------------------------------------------------------------------------

function FileCard({
  fileUrl,
  fileType,
  caption,
}: {
  fileUrl: string;
  fileType: string;
  caption?: string;
}) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = useCallback(async () => {
    setDownloading(true);
    try {
      const resolved = resolveMediaUrl(fileUrl);
      const token = getAccessToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(resolved, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);

      // Trigger browser download without navigating away
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = caption || fileType;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
    } catch (e) {
      console.error("Download failed:", e);
    } finally {
      setDownloading(false);
    }
  }, [fileUrl, fileType, caption]);

  return (
    <button
      type="button"
      className={css.fileCardBtn}
      onClick={handleDownload}
      disabled={downloading}
      aria-label={`Download ${caption || fileType}`}
    >
      <span className={css.fileIcon}>{FILE_ICONS[fileType] ?? "📎"}</span>
      <span className={css.fileLabel}>
        {downloading ? "Downloading…" : (caption || fileType)}
      </span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export default function MediaViewer({
  fileUrl,
  fileType,
  fileTypeDisplay,
  caption,
}: MediaViewerProps) {
  const label = fileTypeDisplay ?? fileType;

  return (
    <div className={css.card}>
      {fileType === "image" ? (
        <ImageCard fileUrl={fileUrl} caption={caption} />
      ) : (
        <FileCard fileUrl={fileUrl} fileType={fileType} caption={caption} />
      )}
      <span className={css.cardInfo}>
        {label}
        {caption ? ` — ${caption}` : ""}
      </span>
    </div>
  );
}
