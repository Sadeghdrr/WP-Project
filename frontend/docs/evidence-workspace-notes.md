# Evidence Workspace – Implementation Notes

## Pages

| Page | Path | File |
|------|------|------|
| Evidence List | `/cases/:caseId/evidence` | `pages/Evidence/EvidenceListPage.tsx` |
| Evidence Detail | `/cases/:caseId/evidence/:evidenceId` | `pages/Evidence/EvidenceDetailPage.tsx` |
| Register Evidence | `/cases/:caseId/evidence/new` | `pages/Evidence/AddEvidencePage.tsx` |

## Architecture

### API Layer (`api/evidence.ts`)
- `fetchEvidence(filters)` — list with query params (type, case, search, etc.)
- `fetchEvidenceDetail(id)` — polymorphic detail (discriminated by `evidence_type`)
- `createEvidence(data)` — POST with discriminated union payload
- `updateEvidence(id, data)` — PATCH
- `deleteEvidence(id)` — DELETE
- `verifyEvidence(id, data)` — coroner verification (approve/reject)
- `linkCase` / `unlinkCase` — associate evidence with additional cases
- `fetchFiles` / `uploadFile` — multipart file management
- `fetchChainOfCustody` — audit trail

### React Query Hooks (`hooks/useEvidence.ts`)
- `useEvidence(filters)` — list query (30s stale)
- `useEvidenceDetail(id)` — detail query (15s stale)
- `useEvidenceFiles(id)` — files query (15s stale)
- `useChainOfCustody(id)` — custody log query (30s stale)
- `useEvidenceActions()` — returns 5 mutations with auto-invalidation

### Helpers (`lib/evidenceHelpers.ts`)
- Type labels, colors (badge classes), icons (emoji)
- File type labels
- Verification status label/color helpers

## Evidence Types
1. **Testimony** — witness statement (`statement_text`)
2. **Biological / Medical** — forensic evidence, coroner verification flow
3. **Vehicle** — model, color, license plate XOR serial number
4. **Identity (ID Document)** — owner name, dynamic key-value document details
5. **Other** — title + description only

## Registration Form (AddEvidencePage)
- Visual type selector (card grid with icons)
- Common fields: title (required), description
- Dynamic sections appear based on selected type
- Vehicle: XOR radio group enforces license plate vs. serial number
- Identity: key-value pair builder for document details
- Client-side validation + backend error display
- Navigates to detail page on success

## Detail Page (EvidenceDetailPage)
- Type-specific detail rendering via `TypeSpecificDetails` switch component
- **Coroner Verification Panel**: visible only for biological evidence + `evidence.can_verify_evidence` permission + not yet verified. Supports approve (requires `forensic_result`) and reject (requires `notes`).
- **File Upload**: multipart via `apiPostForm`, with file type selector and optional caption
- **Chain of Custody Timeline**: chronological audit trail
- **Delete**: confirmation dialog

## Backend Anomalies
None blocking implementation.
