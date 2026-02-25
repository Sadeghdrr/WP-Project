/**
 * Evidence domain types.
 * Maps to: evidence app models (Evidence subtypes, EvidenceFile, EvidenceCustodyLog).
 */

import type { ISODateTime, TimeStamped } from "./common";
import type { UserRef } from "./auth";

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type EvidenceType =
  | "testimony"
  | "biological"
  | "vehicle"
  | "identity"
  | "other";

export type FileType = "image" | "video" | "audio" | "document";

export type CustodyAction =
  | "checked_out"
  | "checked_in"
  | "transferred"
  | "disposed"
  | "analysed";

// ---------------------------------------------------------------------------
// EvidenceFile
// ---------------------------------------------------------------------------

export interface EvidenceFile extends TimeStamped {
  id: number;
  evidence: number;
  file: string; // URL
  file_type: FileType;
  caption: string;
}

// ---------------------------------------------------------------------------
// Evidence (base — discriminated by evidence_type)
// ---------------------------------------------------------------------------

interface EvidenceBase extends TimeStamped {
  id: number;
  case: number;
  title: string;
  description: string;
  registered_by: UserRef;
  files: EvidenceFile[];
}

/** Testimony / witness statement evidence */
export interface TestimonyEvidence extends EvidenceBase {
  evidence_type: "testimony";
  statement_text: string;
}

/** Biological / forensic evidence */
export interface BiologicalEvidence extends EvidenceBase {
  evidence_type: "biological";
  forensic_result: string;
  verified_by: UserRef | null;
  is_verified: boolean;
}

/** Vehicle evidence */
export interface VehicleEvidence extends EvidenceBase {
  evidence_type: "vehicle";
  vehicle_model: string;
  color: string;
  license_plate: string; // XOR with serial_number
  serial_number: string; // XOR with license_plate
}

/** Identity document evidence */
export interface IdentityEvidence extends EvidenceBase {
  evidence_type: "identity";
  owner_full_name: string;
  document_details: Record<string, string>;
}

/** Catch-all other evidence */
export interface OtherEvidence extends EvidenceBase {
  evidence_type: "other";
}

/**
 * Discriminated union of all evidence subtypes.
 * Use `evidence.evidence_type` to narrow.
 */
export type Evidence =
  | TestimonyEvidence
  | BiologicalEvidence
  | VehicleEvidence
  | IdentityEvidence
  | OtherEvidence;

// ---------------------------------------------------------------------------
// EvidenceCustodyLog
// ---------------------------------------------------------------------------

export interface EvidenceCustodyLog {
  id: number;
  evidence: number;
  handled_by: UserRef;
  action_type: CustodyAction;
  timestamp: ISODateTime;
  notes: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// ---------------------------------------------------------------------------
// Request DTOs
// ---------------------------------------------------------------------------

export interface TestimonyCreateRequest {
  case: number;
  title: string;
  description?: string;
  statement_text?: string;
}

export interface BiologicalCreateRequest {
  case: number;
  title: string;
  description?: string;
}

export interface VehicleCreateRequest {
  case: number;
  title: string;
  description?: string;
  vehicle_model: string;
  color: string;
  license_plate?: string;
  serial_number?: string;
}

export interface IdentityCreateRequest {
  case: number;
  title: string;
  description?: string;
  owner_full_name: string;
  document_details?: Record<string, string>;
}

export interface OtherEvidenceCreateRequest {
  case: number;
  title: string;
  description?: string;
}

export interface ForensicResultRequest {
  forensic_result: string;
}

export interface VerifyEvidenceRequest {
  is_verified: boolean;
}

export interface FileUploadMeta {
  file_type: FileType;
  caption?: string;
}
