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
  CaseGenericTransitionRequest,
  ReviewDecisionRequest,
  ResubmitComplaintRequest,
  AssignPersonnelRequest,
  ComplainantCreateRequest,
  ComplainantReviewRequest,
  CaseListItem,
  CaseDetail,
  CaseCalculations,
} from "./cases";
export type { CrimeLevel, CaseStatus, CaseCreationType, ComplainantStatus } from "./cases";

// Evidence
export type {
  Evidence,
  EvidenceListItem,
  TestimonyEvidence,
  BiologicalEvidence,
  VehicleEvidence,
  IdentityEvidence,
  OtherEvidence,
  EvidenceFile,
  EvidenceCustodyLog,
  EvidenceCreateRequest,
  TestimonyCreateRequest,
  BiologicalCreateRequest,
  VehicleCreateRequest,
  IdentityCreateRequest,
  OtherEvidenceCreateRequest,
  VerifyEvidenceRequest,
  LinkCaseRequest,
  UnlinkCaseRequest,
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
  FullBoardState,
  DetectiveBoardListItem,
  ContentObjectSummary,
  BoardNote,
  BoardNoteWithBoard,
  BoardNoteCreateRequest,
  BoardItem,
  BoardItemWithBoard,
  BoardItemCreateRequest,
  BoardItemPositionUpdate,
  BoardConnection,
  BoardConnectionWithBoard,
  BoardConnectionCreateRequest,
  BatchCoordinateUpdateRequest,
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
