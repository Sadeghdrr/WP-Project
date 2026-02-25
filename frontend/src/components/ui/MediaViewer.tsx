/**
 * MediaViewer
 *
 * Renders a clickable thumbnail for an evidence file attachment.
 * For images: delegates to ImageRenderer (auth-aware, lightbox, no double-fetch).
 * For other types: provides a download trigger that appends the JWT.
 */

import { useState, useCallback } from "react";
import { getAccessToken } from "../../api/client";
import { resolveMediaUrl } from "../../lib/mediaUtils";
import ImageRenderer from "./ImageRenderer";
import css from "./MediaViewer.module.css";

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
        <ImageRenderer
          src={fileUrl}
          alt={caption || "Evidence image"}
          caption={caption}
          requiresAuth={true}
          preview={true}
          placeholderIcon="🖼️"
          style={{ width: "100px", height: "100px" }}
        />
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
