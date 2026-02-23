/**
 * Evidence types — mirrors backend evidence.models (polymorphic).
 */
import type { UserListItem } from './user.types';

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

export interface EvidenceListItem {
  id: number;
  evidence_type: EvidenceType;
  title: string;
  description: string;
  case: number;
  registered_by: UserListItem;
  collection_date: string | null;
  verification_status: string | null;
  location: string;
  created_at: string;
}

/** Polymorphic detail — discriminated by evidence_type */
export interface EvidenceDetail extends EvidenceListItem {
  // Testimony-specific
  statement_text?: string;
  // Biological-specific
  forensic_result?: string | null;
  verified_by?: UserListItem | null;
  is_verified?: boolean;
  // Vehicle-specific
  vehicle_model?: string;
  color?: string;
  license_plate?: string | null;
  serial_number?: string | null;
  // Identity-specific
  owner_full_name?: string;
  document_details?: Record<string, string>;
  // Files & custody
  files: EvidenceFile[];
  custody_log: EvidenceCustodyLog[];
  updated_at: string;
}

export interface EvidenceFile {
  id: number;
  file: string;
  file_type: FileType;
  caption: string;
  created_at: string;
}

export interface EvidenceCustodyLog {
  id: number;
  handled_by: UserListItem;
  action_type: CustodyAction;
  timestamp: string;
  notes: string;
}

/* ── Request DTOs ─────────────────────────────────────────────────── */

export interface EvidenceCreateRequest {
  evidence_type: EvidenceType;
  title: string;
  description: string;
  case: number;
  collection_date?: string;
  location?: string;
  // Testimony
  statement_text?: string;
  // Biological — no extra create fields
  // Vehicle
  vehicle_model?: string;
  color?: string;
  license_plate?: string;
  serial_number?: string;
  // Identity
  owner_full_name?: string;
  document_details?: Record<string, string>;
}

export interface EvidenceUpdateRequest {
  title?: string;
  description?: string;
  collection_date?: string;
  location?: string;
}

export interface EvidenceVerifyRequest {
  forensic_result: string;
  is_verified: boolean;
}

export interface EvidenceFilterParams {
  evidence_type?: EvidenceType;
  case?: number;
  is_verified?: boolean;
}
