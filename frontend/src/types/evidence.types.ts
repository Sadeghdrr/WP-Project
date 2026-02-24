/**
 * Evidence types — mirrors backend evidence.models (polymorphic).
 *
 * Corrected to match actual backend serializer output:
 * - EvidenceListSerializer returns registered_by as PK + registered_by_name
 * - Detail serializers include files but NOT custody_log (separate endpoint)
 * - No collection_date, verification_status, or location on base model
 * - Verify endpoint uses { decision, forensic_result, notes }
 */

/* ── Enums (as const objects — erasableSyntaxOnly) ────────────────── */

export const EvidenceType = {
  TESTIMONY: 'testimony',
  BIOLOGICAL: 'biological',
  VEHICLE: 'vehicle',
  IDENTITY: 'identity',
  OTHER: 'other',
} as const;
export type EvidenceType = (typeof EvidenceType)[keyof typeof EvidenceType];

export const FileType = {
  IMAGE: 'image',
  VIDEO: 'video',
  AUDIO: 'audio',
  DOCUMENT: 'document',
} as const;
export type FileType = (typeof FileType)[keyof typeof FileType];

export const CustodyAction = {
  CHECKED_OUT: 'checked_out',
  CHECKED_IN: 'checked_in',
  TRANSFERRED: 'transferred',
  DISPOSED: 'disposed',
  ANALYSED: 'analysed',
} as const;
export type CustodyAction = (typeof CustodyAction)[keyof typeof CustodyAction];

/* ── Base evidence ────────────────────────────────────────────────── */

/**
 * Matches backend EvidenceListSerializer output.
 * registered_by is a PK integer; registered_by_name is the full name string.
 */
export interface EvidenceListItem {
  id: number;
  evidence_type: EvidenceType;
  evidence_type_display: string;
  title: string;
  description: string;
  case: number;
  registered_by: number;
  registered_by_name: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Polymorphic detail — discriminated by evidence_type.
 * Backend detail serializers include files[] but custody_log is fetched
 * separately via GET /api/evidence/{id}/chain-of-custody/.
 */
export interface EvidenceDetail extends EvidenceListItem {
  // Testimony-specific
  statement_text?: string;
  // Biological-specific
  forensic_result?: string | null;
  verified_by?: number | null;
  verified_by_name?: string | null;
  is_verified?: boolean;
  // Vehicle-specific
  vehicle_model?: string;
  color?: string;
  license_plate?: string | null;
  serial_number?: string | null;
  // Identity-specific
  owner_full_name?: string;
  document_details?: Record<string, string>;
  // Files (included in detail response)
  files: EvidenceFile[];
}

export interface EvidenceFile {
  id: number;
  file: string;
  file_type: FileType;
  file_type_display?: string;
  caption: string;
  created_at: string;
}

/**
 * Chain-of-custody entry — matches backend ChainOfCustodyEntrySerializer.
 * Field mapping: action_type→action, handled_by→performed_by, notes→details.
 */
export interface EvidenceCustodyLog {
  id: number;
  timestamp: string;
  action: string;
  performed_by: number;
  performer_name: string | null;
  details: string;
}

/* ── Request DTOs ─────────────────────────────────────────────────── */

/**
 * Polymorphic create request — matches backend create serializers.
 * No collection_date or location fields (not in backend model).
 */
export interface EvidenceCreateRequest {
  evidence_type: EvidenceType;
  title: string;
  description: string;
  case: number;
  // Testimony
  statement_text?: string;
  // Biological — no extra create fields (forensic_result set by Coroner later)
  // Vehicle
  vehicle_model?: string;
  color?: string;
  license_plate?: string;
  serial_number?: string;
  // Identity
  owner_full_name?: string;
  document_details?: Record<string, string>;
}

/**
 * Update request — matches backend EvidenceUpdateSerializer.
 * Only title and description are mutable on the base model.
 * Type-specific update serializers allow additional fields.
 */
export interface EvidenceUpdateRequest {
  title?: string;
  description?: string;
  // Testimony update
  statement_text?: string;
  // Vehicle update
  vehicle_model?: string;
  color?: string;
  license_plate?: string;
  serial_number?: string;
  // Identity update
  owner_full_name?: string;
  document_details?: Record<string, string>;
}

/**
 * Coroner verification request — matches backend VerifyBiologicalEvidenceSerializer.
 * Uses decision ("approve"/"reject"), forensic_result, and notes.
 */
export interface EvidenceVerifyRequest {
  decision: 'approve' | 'reject';
  forensic_result?: string;
  notes?: string;
}

export interface EvidenceFilterParams {
  evidence_type?: EvidenceType;
  case?: number;
  is_verified?: boolean;
}
