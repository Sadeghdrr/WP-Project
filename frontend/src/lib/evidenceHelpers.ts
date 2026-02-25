/**
 * Evidence display helpers — type labels, colors, and metadata.
 */

import type { EvidenceType } from "../types";

// ---------------------------------------------------------------------------
// Evidence type labels
// ---------------------------------------------------------------------------

export const EVIDENCE_TYPE_LABELS: Record<EvidenceType, string> = {
  testimony: "Testimony",
  biological: "Biological / Medical",
  vehicle: "Vehicle",
  identity: "ID Document",
  other: "Other Item",
};

// ---------------------------------------------------------------------------
// Evidence type colors (CSS class suffixes)
// ---------------------------------------------------------------------------

export type EvidenceColor = "blue" | "red" | "amber" | "purple" | "gray";

export const EVIDENCE_TYPE_COLORS: Record<EvidenceType, EvidenceColor> = {
  testimony: "blue",
  biological: "red",
  vehicle: "amber",
  identity: "purple",
  other: "gray",
};

// ---------------------------------------------------------------------------
// Evidence type icons (emoji for lightweight display)
// ---------------------------------------------------------------------------

export const EVIDENCE_TYPE_ICONS: Record<EvidenceType, string> = {
  testimony: "🗣️",
  biological: "🧬",
  vehicle: "🚗",
  identity: "🪪",
  other: "📦",
};

// ---------------------------------------------------------------------------
// File type helpers
// ---------------------------------------------------------------------------

export const FILE_TYPE_LABELS: Record<string, string> = {
  image: "Image",
  video: "Video",
  audio: "Audio",
  document: "Document",
};

// ---------------------------------------------------------------------------
// Verification status helpers
// ---------------------------------------------------------------------------

export function getVerificationLabel(isVerified: boolean): string {
  return isVerified ? "Verified" : "Pending Verification";
}

export function getVerificationColor(isVerified: boolean): "green" | "amber" {
  return isVerified ? "green" : "amber";
}
