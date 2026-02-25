/**
 * Evidence domain types.
 * Maps to: evidence app models (Evidence subtypes, EvidenceFile, EvidenceCustodyLog).
 */

import type { ISODateTime } from "./common";

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

export interface EvidenceFile {
  id: number;
  file: string; // URL
  file_type: FileType;
  file_type_display: string;
  caption: string;
  created_at: ISODateTime;
}

// ---------------------------------------------------------------------------
// Evidence list item (compact — from EvidenceListSerializer)
// ---------------------------------------------------------------------------

export interface EvidenceListItem {
  id: number;
  title: string;
  description: string;
  evidence_type: EvidenceType;
  evidence_type_display: string;
  case: number;
  registered_by: number;
  registered_by_name: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// ---------------------------------------------------------------------------
// Evidence detail (polymorphic — discriminated by evidence_type)
// ---------------------------------------------------------------------------

interface EvidenceDetailBase {
  id: number;
  case: number;
  title: string;
  description: string;
  evidence_type_display: string;
  registered_by: number;
  registered_by_name: string | null;
  files: EvidenceFile[];
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

/** Testimony / witness statement evidence */
export interface TestimonyEvidence extends EvidenceDetailBase {
  evidence_type: "testimony";
  statement_text: string;
}

/** Biological / forensic evidence */
export interface BiologicalEvidence extends EvidenceDetailBase {
  evidence_type: "biological";
  forensic_result: string;
  is_verified: boolean;
  verified_by: number | null;
  verified_by_name: string | null;
}

/** Vehicle evidence */
export interface VehicleEvidence extends EvidenceDetailBase {
  evidence_type: "vehicle";
  vehicle_model: string;
  color: string;
  license_plate: string; // XOR with serial_number
  serial_number: string; // XOR with license_plate
}

/** Identity document evidence */
export interface IdentityEvidence extends EvidenceDetailBase {
  evidence_type: "identity";
  owner_full_name: string;
  document_details: Record<string, string>;
}

/** Catch-all other evidence */
export interface OtherEvidence extends EvidenceDetailBase {
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
// EvidenceCustodyLog (from ChainOfCustodyEntrySerializer)
// ---------------------------------------------------------------------------

export interface EvidenceCustodyLog {
  id: number;
  timestamp: ISODateTime;
  action: string;          // display label
  performed_by: number;    // user PK
  performer_name: string | null;
  details: string;         // notes
}

// ---------------------------------------------------------------------------
// Request DTOs
// ---------------------------------------------------------------------------

export interface TestimonyCreateRequest {
  evidence_type: "testimony";
  case: number;
  title: string;
  description?: string;
  statement_text?: string;
}

export interface BiologicalCreateRequest {
  evidence_type: "biological";
  case: number;
  title: string;
  description?: string;
}

export interface VehicleCreateRequest {
  evidence_type: "vehicle";
  case: number;
  title: string;
  description?: string;
  vehicle_model: string;
  color: string;
  license_plate?: string;
  serial_number?: string;
}

export interface IdentityCreateRequest {
  evidence_type: "identity";
  case: number;
  title: string;
  description?: string;
  owner_full_name: string;
  document_details?: Record<string, string>;
}

export interface OtherEvidenceCreateRequest {
  evidence_type: "other";
  case: number;
  title: string;
  description?: string;
}

export type EvidenceCreateRequest =
  | TestimonyCreateRequest
  | BiologicalCreateRequest
  | VehicleCreateRequest
  | IdentityCreateRequest
  | OtherEvidenceCreateRequest;

/** POST /api/evidence/{id}/verify/ */
export interface VerifyEvidenceRequest {
  decision: "approve" | "reject";
  forensic_result?: string;
  notes?: string;
}

/** POST /api/evidence/{id}/link-case/ */
export interface LinkCaseRequest {
  case_id: number;
}

/** POST /api/evidence/{id}/unlink-case/ */
export interface UnlinkCaseRequest {
  case_id: number;
}

export interface FileUploadMeta {
  file_type: FileType;
  caption?: string;
}
