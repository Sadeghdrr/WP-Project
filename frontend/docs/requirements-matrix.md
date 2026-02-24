# Frontend Requirements & Scoring Matrix

> Source of truth: `md-files/project-doc.md` — Chapter 5 (Required Pages), Chapter 7 (CP2 Scoring), Chapter 4 (Flows), Chapter 2 (User Levels).
> Generated: 2026-02-25 | Branch: `agent/step-01-frontend-requirements-matrix`

---

## 1. Page-Level Requirements (3000 pts total)

### 1.1 Home Page — 200 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| HP-1 | General introduction to the system and police department | §5.1 | Required | Static/markdown content block describing the system |
| HP-2 | Display at least 3 statistics about cases | §5.1 | Required | Show: total solved cases, total employees, active cases (or equivalent) |
| HP-3 | Statistics fetched from backend aggregation API | §5.1, §7 | Required | Data loaded from `GET /api/core/statistics/` or equivalent |

**Acceptance checklist:**
- [ ] Landing page renders introduction text
- [ ] At least 3 live statistics displayed
- [ ] Loading/skeleton shown while stats load
- [ ] Responsive layout

---

### 1.2 Login & Registration Page — 200 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| LR-1 | Registration form: username, password, email, phone, full name, national ID | §4.1 | Required | All fields present and validated |
| LR-2 | Login via password + one of: username, national ID, phone, email | §4.1 | Required | User can choose login identifier |
| LR-3 | All identifier fields must be unique (show validation errors) | §4.1 | Required | Backend-driven uniqueness errors surfaced to user |
| LR-4 | Dedicated page (not a modal) | §5.2 | Required | Separate route for auth |

**Acceptance checklist:**
- [ ] Registration form with all 6 fields + validation
- [ ] Login form with identifier selector + password
- [ ] Error messages on failure
- [ ] Redirect to dashboard on success
- [ ] Responsive layout

---

### 1.3 Modular Dashboard — 800 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| MD-1 | Role-based modular dashboard | §5.3 | Required | Dashboard displays modules based on user's role |
| MD-2 | Modules shown per access level | §5.3 | Required | Detective sees "Detective Board" module; Coroner does not |
| MD-3 | Module examples: auditing, case review, complaint review | §5.3 | Required | At minimum, role-appropriate navigation + summary cards |
| MD-4 | Each role's dashboard reflects their primary actions and visible data | §5.3, §3.1 | Required | See Role→Module mapping table below |

**Role → Dashboard Module Mapping** (derived from §2.2, §3.1, §4.x, §5.3):

| Role | Dashboard Modules |
|---|---|
| System Admin | User Management, Role Management, Permission Assignment, System Overview |
| Police Chief | Case Overview, Critical Case Approval, Trial Referral, Most Wanted Summary |
| Captain | Case Approval, Trial Referral, Suspect Verdicts, Reporting |
| Sergeant | Case Supervision, Suspect Approval, Interrogation, Bail Management, Arrest Warrants |
| Detective | Detective Board, Case Investigation, Evidence Review, Suspect Identification, Notifications |
| Police Officer | Crime Scene Registration, Case Review (assigned), Bounty Tip Review |
| Patrol Officer | Crime Scene Reporting, Evidence Registration |
| Cadet | Complaint Review/Filter, Case Forwarding |
| Coroner | Evidence Verification (biological/medical) |
| Judge | Trial Management, Case File Review, Verdict Recording |
| Complainant | File Complaint, My Cases, Complaint Status |
| Witness | View Associated Cases |
| Suspect | View Own Case, View Bail Status |
| Criminal | View Own Case, View Bail Status |
| Base User | Most Wanted (view), Submit Bounty Tip |

**Acceptance checklist:**
- [ ] Dashboard renders differently per role
- [ ] Module visibility controlled by role permissions
- [ ] Navigation to each module works
- [ ] Loading/skeleton states
- [ ] Responsive layout

---

### 1.4 Detective Board — 800 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| DB-1 | Display documents/notes on a board | §5.4, §4.4 | Required | Canvas/board with document cards |
| DB-2 | Connect documents with red lines | §5.4 | Required | Clickable connection mechanism, red line rendering |
| DB-3 | Drag-and-drop placement of documents/notes | §5.4 | Required | Freely movable items on the board |
| DB-4 | Lines addable and removable | §5.4 | Required | User can add/remove connections |
| DB-5 | Export board as image | §5.4 | Required | Download/export button producing PNG/JPEG |
| DB-6 | Detective declares suspects to Sergeant | §4.4 | Required | Action to submit suspect list for approval |
| DB-7 | Approval/rejection flow with messages | §4.4 | Required | Sergeant approval notification; rejection returns message to Detective |
| DB-8 | Notification when new evidence added to case | §4.4 | Required | Visual indicator of new evidence (polling-based) |

**Acceptance checklist:**
- [ ] Board canvas renders with documents/notes
- [ ] Red-line connections between items
- [ ] Drag-and-drop repositioning
- [ ] Add/remove connections
- [ ] Export as image
- [ ] Suspect declaration UI
- [ ] Notification badge for new evidence
- [ ] Responsive (reasonable on smaller screens)

---

### 1.5 Most Wanted — 300 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| MW-1 | Display heavily wanted criminals/suspects | §5.5, §4.7 | Required | List/grid of most-wanted individuals |
| MW-2 | Photos and details displayed | §4.7 | Required | Photo, name, details per person |
| MW-3 | Ranking by score = max_days_wanted × highest_crime_degree | §4.7 Note 1 | Required | Ordered list; score from backend |
| MW-4 | Bounty amount displayed below each person | §4.7 Note 2 | Required | Reward amount from backend `computed_reward` field |
| MW-5 | "Wanted > 30 days" threshold for inclusion | §4.7 | Required | Only show suspects wanted > 30 days |
| MW-6 | Visible to all authenticated users (including Base User) | §4.7, A7 resolution | Required | No role restriction beyond authentication |

**Backend note:** Ranking and bounty are calculated server-side. Frontend displays only.

**A7 Resolution:** The doc says "visible to all users." Backend requires authentication but grants access to Base User role. Unauthenticated users cannot view. If public access is desired, backend would need `AllowAny` — document as minor gap.

**Acceptance checklist:**
- [ ] Most wanted list renders with photos + details
- [ ] Sorted by ranking score
- [ ] Bounty displayed per person
- [ ] Accessible to all logged-in users
- [ ] Loading/skeleton state
- [ ] Responsive layout

---

### 1.6 Case & Complaint Status — 200 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| CS-1 | Users see cases/complaints relevant to them | §5.6 | Required | Filtered by role + assignment |
| CS-2 | Edit if permitted | §5.6 | Required | Role-based edit capability |
| CS-3 | Complaint registration flow (Complainant → Cadet → Police Officer) | §4.2.1 | Required | Multi-step status progression |
| CS-4 | Cadet return-with-error-message | §4.2.1 | Required | Error message field on rejection |
| CS-5 | 3-strike voiding of complaint | §4.2.1 | Required | Counter visible; auto-void after 3 |
| CS-6 | Crime scene registration flow | §4.2.2 | Required | Police rank creates case with witnesses |
| CS-7 | Approve/reject/forward actions per role | §4.2.1, §4.2.2 | Required | Action buttons per current status |
| CS-8 | Status tracking and progression display | §5.6 | Required | Visual status indicator |

**Acceptance checklist:**
- [ ] Case list filtered by user role/assignment
- [ ] Case detail view with full info
- [ ] Complaint submission form (Complainant)
- [ ] Cadet review form with reject+message
- [ ] Crime scene registration form
- [ ] Status progression visible
- [ ] Responsive layout

---

### 1.7 General Reporting — 300 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| GR-1 | Complete case report: creation date, evidence, testimonies, suspects, criminal, complainant(s) | §5.7 | Required | All data fields displayed |
| GR-2 | Names and ranks of all involved personnel | §5.7 | Required | Personnel list with rank labels |
| GR-3 | Primarily for Judge, Captain, Police Chief | §5.7 | Required | Access restricted to these roles |
| GR-4 | Every approved/rejected report with specifics | §4.6, §5.7 | Required | Decision history shown |

**Acceptance checklist:**
- [ ] Full case report view with all entities
- [ ] Personnel involved listed with ranks
- [ ] Role-restricted access
- [ ] Printable/exportable format (recommended)
- [ ] Loading/skeleton state
- [ ] Responsive layout

---

### 1.8 Evidence Registration & Review — 200 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| ER-1 | Register witness/local testimonies (text, images, video, audio) | §4.3.1 | Required | Form with media upload |
| ER-2 | Register biological/medical evidence (title, description, images, follow-up result) | §4.3.2 | Required | Form with image upload + pending result field |
| ER-3 | Register vehicle evidence (model, plate/serial, color) | §4.3.3 | Required | Form with plate XOR serial validation |
| ER-4 | Register ID document evidence (name + key-value pairs) | §4.3.4 | Required | Dynamic key-value form |
| ER-5 | Register other evidence (title + description) | §4.3.5 | Required | Simple form |
| ER-6 | Review evidence per access level | §5.8 | Required | Role-filtered evidence list |
| ER-7 | Coroner verifies/rejects biological evidence | §3.1.2, §4.3.2 | Required | Approve/reject action for Coroner |
| ER-8 | All evidence has title, description, registration date, registrar | §4.3 | Required | Common fields on all forms |

**Acceptance checklist:**
- [ ] Forms for each evidence subtype
- [ ] File/image upload working
- [ ] Vehicle plate XOR serial validation
- [ ] Dynamic key-value UI for ID docs
- [ ] Evidence list with role-based filtering
- [ ] Coroner verify/reject UI
- [ ] Responsive layout

---

### 1.9 Admin Panel — 200 pts

| # | Requirement | Source | Priority | Acceptance Criteria |
|---|---|---|---|---|
| AP-1 | Custom admin panel (non-Django, similar functionality) | §7 | Required | React-based admin UI |
| AP-2 | User management: list, activate, deactivate, assign roles | §2.2, §4.1, backend API | Required | CRUD on users via `/api/accounts/users/` |
| AP-3 | Role management: create, edit, delete roles | §2.2 (roles are dynamic) | Required | CRUD on roles via `/api/accounts/roles/` |
| AP-4 | Permission assignment to roles | §2.2 | Required | Permission picker + assign action |
| AP-5 | Roles modifiable without code changes | §2.2, §6 (CP1 scoring) | Required | UI-driven role management |

**A1 Resolution:** Admin Panel is scored at 200 pts in §7. Not detailed in §5 (Required Pages), but backend fully supports admin API endpoints. Implement minimal admin features: user list, role CRUD, permission assignment.

**Acceptance checklist:**
- [ ] User list with search/filter
- [ ] Activate/deactivate users
- [ ] Assign role to user
- [ ] Role CRUD
- [ ] Permission picker and assignment
- [ ] Responsive layout

---

## 2. Flow/Process Requirements (Frontend support for Ch. 4 flows)

These are implicit frontend requirements derived from process flows that must be surfaced through the pages above.

| # | Flow | Pages Involved | Key Frontend Actions |
|---|---|---|---|
| FL-1 | Registration & Login (§4.1) | Login/Registration Page | Register form, login form, token handling |
| FL-2 | Case Creation via Complaint (§4.2.1) | Case & Complaint Status | Complaint form → Cadet review → Police Officer review |
| FL-3 | Case Creation via Crime Scene (§4.2.2) | Case & Complaint Status | Crime scene form with witness info |
| FL-4 | Evidence Registration (§4.3) | Evidence Registration & Review | 5 evidence subtypes with forms |
| FL-5 | Solving the Case (§4.4) | Detective Board | Board canvas, suspect declaration, approval flow |
| FL-6 | Suspect Identification & Interrogation (§4.5) | Case & Complaint Status, Dashboard | Guilt probability (1–10) input for Detective + Sergeant |
| FL-7 | Trial (§4.6) | General Reporting, Dashboard | Judge views full case, records verdict + punishment |
| FL-8 | Suspect Status (§4.7) | Most Wanted | Automatic display of wanted > 30 days |
| FL-9 | Bounty (§4.8) | Dashboard (Police Officer, Detective) | Tip submission, review, verification, reward code display |
| FL-10 | Bail & Fines (§4.9) | Dashboard (Sergeant, Suspect) | **Optional** — bail payment UI if backend supports |

---

## 3. Cross-Cutting / Non-Functional Requirements (1550 pts total)

| # | Requirement | Source | Points | Priority | Acceptance Criteria |
|---|---|---|---|---|---|
| XC-1 | Loading states & skeleton layouts | §7 | 300 | Required | Every async data load shows skeleton/spinner |
| XC-2 | Full project Dockerization with Docker Compose | §7 | 300 | Required | `docker-compose up` runs frontend + backend + DB |
| XC-3 | At least 5 frontend tests | §7 | 100 | Required | 5+ test cases passing (component/integration) |
| XC-4 | Proper state management | §7 | 100 | Required | Consistent state approach (Context, Zustand, etc.) |
| XC-5 | Responsive pages | §7 | 300 | Required | All pages usable on mobile/tablet/desktop |
| XC-6 | Best practices (as taught in class) | §7 | 150 | Required | Clean components, separation of concerns |
| XC-7 | Component lifecycle management | §7 | 100 | Required | Proper useEffect cleanup, no memory leaks |
| XC-8 | Error messages per situation | §7 | 100 | Required | Contextual error display for API failures, validation |
| XC-9 | Code modifiability | §7 | 100 | Required | Modular architecture, easy to extend |

---

## 4. Constraints & Rules

| # | Constraint | Source | Details |
|---|---|---|---|
| CN-1 | Max 6 NPM packages | §1.4 | Runtime dependencies only. React, Vite, TypeScript, SWC, ESLint, dev tooling excluded. Currently 2 used (react, react-dom). 4 slots remaining. |
| CN-2 | Tech stack: React (or NextJS) | §2.3, §1.1 | Using React + Vite + TS + SWC (confirmed) |
| CN-3 | Public repository with ≥15 commits per checkpoint | §1.2 | Commits must be meaningful |
| CN-4 | Final report required for grade | §1.4 | No report = 0 points |
| CN-5 | No code changes needed for role modification | §2.2 | Admin UI must support dynamic role management |

---

## 5. Optional / Stretch Requirements

| # | Requirement | Source | Notes |
|---|---|---|---|
| OPT-1 | Bail Payment UI (§4.9) | §4.9 | Explicitly marked "(Optional)" in project doc. Backend supports it. Implement if time permits; must NOT block CP2 scoring. |
| OPT-2 | Payment gateway integration | §4.9, §6 | Connected to OPT-1. Backend has stub-level support (payment reference string). |

---

## 6. Scoring Summary

| Category | Points | % of Total |
|---|---|---|
| Pages (UI/UX) | 3000 | 65.9% |
| Loading/Skeletons | 300 | 6.6% |
| Docker Compose | 300 | 6.6% |
| Responsive | 300 | 6.6% |
| Best Practices | 150 | 3.3% |
| State Management | 100 | 2.2% |
| Frontend Tests | 100 | 2.2% |
| Component Lifecycles | 100 | 2.2% |
| Error Messages | 100 | 2.2% |
| Code Modifiability | 100 | 2.2% |
| **Total** | **4550** | **100%** |

> **Note:** The 200 pts for bail payment (§6, CP1) are in the CP1 scoring, not CP2. The optional bail flow (§4.9) does not have separate CP2 points — it is bundled within page scores if implemented.
