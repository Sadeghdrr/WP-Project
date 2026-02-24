# Frontend Scope Summary

> What the frontend must deliver for CP2.
> Source: `md-files/project-doc.md` | Generated: 2026-02-25

---

## System Overview

A React-based web application for the LAPD's case management system (inspired by L.A. Noire). The frontend connects to a Django REST backend and must present role-based interfaces for 12+ user roles across police, judiciary, civilian, and admin functions.

---

## Pages to Build (9 total)

1. **Home Page** — Public landing with system intro + 3+ live statistics (solved cases, employees, active cases).

2. **Login & Registration** — Register with username/password/email/phone/name/national-ID. Login with password + any unique identifier.

3. **Modular Dashboard** — Role-aware dashboard showing only the modules relevant to the logged-in user's role. Each role sees a different set of action cards/navigation.

4. **Detective Board** — Interactive canvas with drag-and-drop document/note cards, red-line connections between them, and image export. Core tool for case-solving flow.

5. **Most Wanted** — Ranked list of suspects wanted > 30 days with photos, details, and bounty amounts. Data and ranking from backend.

6. **Case & Complaint Status** — Case lifecycle management: complaint submission (Complainant), review (Cadet → Police Officer), crime scene registration, status tracking, approve/reject actions.

7. **General Reporting** — Full case reports with evidence, testimonies, suspects, personnel, and decision history. Primarily for Judge, Captain, Police Chief.

8. **Evidence Registration & Review** — Forms for 5 evidence subtypes (testimonies, biological, vehicles, ID documents, other). Coroner verification workflow.

9. **Admin Panel** — React-based (not Django admin). User management, role CRUD, permission assignment. Enables dynamic role changes without code modifications.

---

## Key Flows the Frontend Must Support

| Flow | What the user does |
|---|---|
| Register & Login | Create account → get role assigned by admin → log in |
| File Complaint | Complainant submits case → Cadet reviews → Police Officer approves/rejects |
| Report Crime Scene | Police rank logs scene + witnesses → superior approves |
| Register Evidence | Detectives/officers add evidence (5 subtypes) to a case |
| Solve Case | Detective uses board to link evidence → declares suspects → Sergeant approves |
| Interrogation | Sergeant + Detective assign guilt scores (1–10) → Captain/Chief decides |
| Trial | Judge reviews full case → records verdict + punishment |
| Most Wanted | Auto-populated list of suspects wanted > 30 days |
| Bounty Tips | Base user submits tip → Police Officer reviews → Detective verifies → reward code issued |
| Bail (optional) | Sergeant sets bail → suspect pays via gateway reference |

---

## Non-Functional Requirements

| Requirement | Impact |
|---|---|
| **Loading & skeletons** | Every data-loading state must show skeleton/spinner (300 pts) |
| **Responsive design** | All pages must work on mobile, tablet, desktop (300 pts) |
| **Docker Compose** | `docker-compose up` runs frontend + backend + Postgres (300 pts) |
| **State management** | Consistent pattern across the app (100 pts) |
| **5+ frontend tests** | Component or integration tests (100 pts) |
| **Error handling** | Contextual error messages for every failure mode (100 pts) |
| **Component lifecycles** | Proper cleanup, no memory leaks (100 pts) |
| **Best practices** | Clean code, separation of concerns (150 pts) |
| **Code modifiability** | Easy to add/change features (100 pts) |

---

## Hard Constraints

1. **Max 6 runtime NPM packages** (excluding React, Vite, TypeScript, SWC, ESLint, dev tools). Currently 2 used (react, react-dom) — 4 slots free.
2. **React + Vite + TypeScript + SWC** stack (confirmed).
3. **15+ meaningful commits** required for this checkpoint.
4. **All roles dynamically manageable** via admin UI — no hardcoded role logic that requires code changes.

---

## What Frontend Does NOT Do

- **No ranking/bounty calculation** — backend computes and serves these.
- **No real-time push** — backend provides polling-based notifications only (REST API).
- **No payment gateway SDK** — backend accepts a payment reference string; frontend passes it through.
- **No backend modifications** — use existing API endpoints as-is (flag gaps if found).

---

## Scoring Breakdown

| Category | Points |
|---|---|
| 9 Pages (UI/UX) | 3,000 |
| Loading/Skeletons | 300 |
| Docker Compose | 300 |
| Responsive Design | 300 |
| Best Practices | 150 |
| State Management | 100 |
| Frontend Tests | 100 |
| Component Lifecycles | 100 |
| Error Messages | 100 |
| Code Modifiability | 100 |
| **Total** | **4,550** |
