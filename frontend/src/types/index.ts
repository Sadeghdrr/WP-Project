/**
 * Barrel export for all domain types.
 *
 * Usage:
 *   import type { Case, User, Evidence } from "@/types";
 *
 * Note: Path alias "@" → "src/" will be configured when the router package
 * is installed (Step 04+).
 */

// Common / shared
export type { ISODateTime, PaginatedResponse, TimeStamped, ApiError, EntityId } from "./common";

// Auth & accounts
export type {
  Permission,
  Role,
  RoleDetail,
  RoleRef,
  User,
  UserRef,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  TokenPair,
  TokenRefreshRequest,
  TokenRefreshResponse,
  JwtPayload,
  RoleCreateRequest,
  RoleUpdateRequest,
  UserUpdateRoleRequest,
} from "./auth";

// Cases
export type {
  Case,
  CaseRef,
  CaseComplainant,
  CaseWitness,
  CaseStatusLog,
  CaseCreateComplaintRequest,
  CaseCreateCrimeSceneRequest,
  CaseStatusTransitionRequest,
  ComplainantCreateRequest,
  ComplainantReviewRequest,
} from "./cases";
export type { CrimeLevel, CaseStatus, CaseCreationType, ComplainantStatus } from "./cases";

// Evidence
export type {
  Evidence,
  TestimonyEvidence,
  BiologicalEvidence,
  VehicleEvidence,
  IdentityEvidence,
  OtherEvidence,
  EvidenceFile,
  EvidenceCustodyLog,
  TestimonyCreateRequest,
  BiologicalCreateRequest,
  VehicleCreateRequest,
  IdentityCreateRequest,
  OtherEvidenceCreateRequest,
  ForensicResultRequest,
  VerifyEvidenceRequest,
  FileUploadMeta,
} from "./evidence";
export type { EvidenceType, FileType, CustodyAction } from "./evidence";

// Suspects
export type {
  Suspect,
  MostWantedEntry,
  Warrant,
  Interrogation,
  InterrogationCreateRequest,
  Trial,
  TrialCreateRequest,
  BountyTip,
  BountyTipCreateRequest,
  BountyTipReviewRequest,
  BountyTipVerifyRequest,
  BountyVerifyLookupRequest,
  BountyVerifyLookupResponse,
  Bail,
  BailCreateRequest,
  SuspectStatusLog,
  SuspectCreateRequest,
  SuspectApprovalRequest,
} from "./suspects";
export type {
  SuspectStatus,
  WarrantStatus,
  WarrantPriority,
  VerdictChoice,
  BountyTipStatus,
  SergeantApprovalStatus,
} from "./suspects";

// Board
export type {
  DetectiveBoard,
  BoardNote,
  BoardNoteCreateRequest,
  BoardItem,
  BoardItemCreateRequest,
  BoardItemPositionUpdate,
  BoardConnection,
  BoardConnectionCreateRequest,
} from "./board";

// Core
export type {
  Notification,
  NotificationMarkReadRequest,
  DashboardStats,
  SearchCategory,
  SearchCaseResult,
  SearchSuspectResult,
  SearchEvidenceResult,
  GlobalSearchResponse,
  SystemConstants,
  ChoiceItem,
  RoleHierarchyItem,
} from "./core";
