# Suspects Services — Arrest & Warrant Pipeline Report

## Overview

This report documents the implementation of the suspect arrest pipeline:
**Warrant Issuance → Arrest Execution → Status Transitions**, including
concurrency controls and audit logging.

All business logic resides in `ArrestAndWarrantService` (Fat Services,
Skinny Views architecture).

---

## 1. State Transition Matrix

The following table shows every allowed status transition enforced by
`ArrestAndWarrantService.transition_status` and `execute_arrest`:

| # | Current State          | → Next State            | Required Permission             | Trigger Method         |
|---|------------------------|-------------------------|---------------------------------|------------------------|
| 1 | `wanted`               | → `arrested`            | `can_issue_arrest_warrant`      | `execute_arrest()`     |
| 2 | `arrested`             | → `under_interrogation` | `can_conduct_interrogation`     | `transition_status()`  |
| 3 | `arrested`             | → `released`            | `can_set_bail_amount`           | `transition_status()`  |
| 4 | `under_interrogation`  | → `under_trial`         | `can_render_verdict`            | `transition_status()`  |
| 5 | `under_trial`          | → `convicted`           | `can_judge_trial`               | `transition_status()`  |
| 6 | `under_trial`          | → `acquitted`           | `can_judge_trial`               | `transition_status()`  |
| 7 | `convicted`            | → `released`            | `can_set_bail_amount`           | `transition_status()`  |
| 8 | `acquitted`            | _(terminal state)_      | —                               | —                      |
| 9 | `released`             | _(terminal state)_      | —                               | —                      |

Any transition not listed above raises `InvalidTransition` (HTTP 409/400).

### State Machine Diagram

```
WANTED ──► ARRESTED ──► UNDER_INTERROGATION ──► UNDER_TRIAL ──► CONVICTED ──► RELEASED
               │                                      │
               └──► RELEASED (bail)                    └──► ACQUITTED (terminal)
```

---

## 2. Concurrency Strategy

### Problem
Multiple officers might attempt to transition a suspect's status
simultaneously (e.g., two arrest attempts on the same suspect, or
a bail release racing with an interrogation start).

### Solution: `select_for_update()`

Both `transition_status()` and `execute_arrest()` use the following
pattern inside `@transaction.atomic`:

```python
suspect = Suspect.objects.select_for_update().select_related(
    "case",
).get(pk=suspect_id)
```

This acquires a **row-level lock** on the suspect record for the
duration of the transaction, ensuring that:

1. Only one status transition can proceed at a time for a given suspect.
2. The second concurrent request will block until the first completes,
   then re-read the current status — and likely fail the state-machine
   guard (e.g., suspect is no longer `WANTED`).
3. No phantom writes or lost updates can occur.

### Audit Trail

Every transition (including arrests) creates an immutable
`SuspectStatusLog` entry recording:
- `from_status` / `to_status`
- `changed_by` (the acting user)
- `notes` (justification, arrest location, warrant info)
- `created_at` (auto-timestamped)

---

## 3. API Sequences

### 3.1 Issuing an Arrest Warrant

**Endpoint:** `POST /api/suspects/{id}/issue-warrant/`

**Prerequisites:**
- Suspect must be approved (`sergeant_approval_status == "approved"`)
- Suspect must be in `wanted` status
- No duplicate active warrant may exist
- Actor must have `can_issue_arrest_warrant` permission (Sergeant+)

```bash
curl -X POST http://localhost:8000/api/suspects/12/issue-warrant/ \
  -H "Authorization: Bearer <sergeant_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "warrant_reason": "Strong forensic evidence linking suspect to murder weapon found at scene.",
    "priority": "high"
  }'
```

**Success Response (200):**
```json
{
  "id": 12,
  "full_name": "Roy Earle",
  "status": "wanted",
  "status_display": "Wanted",
  "sergeant_approval_status": "approved",
  "...": "..."
}
```

**Error — Not approved (400):**
```json
{
  "detail": "Suspect must be approved by a sergeant before a warrant can be issued."
}
```

---

### 3.2 Attempting an Invalid Status Transition (Should Fail)

**Endpoint:** `POST /api/suspects/{id}/transition-status/`

Trying to move a `wanted` suspect directly to `under_interrogation`
(skipping the `arrested` state):

```bash
curl -X POST http://localhost:8000/api/suspects/12/transition-status/ \
  -H "Authorization: Bearer <sergeant_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "new_status": "under_interrogation",
    "reason": "Attempting to skip arrest step."
  }'
```

**Error Response (400):**
```json
{
  "detail": "Invalid state transition from 'Wanted' to 'under_interrogation' — Transition from 'Wanted' to 'under_interrogation' is not allowed."
}
```

---

### 3.3 Executing an Arrest Successfully

**Endpoint:** `POST /api/suspects/{id}/arrest/`

**Prerequisites:**
- Active warrant exists (or `warrant_override_justification` provided)
- Suspect in `wanted` status and approved
- Actor has `can_issue_arrest_warrant` permission

```bash
curl -X POST http://localhost:8000/api/suspects/12/arrest/ \
  -H "Authorization: Bearer <sergeant_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "arrest_location": "742 S. Broadway, Los Angeles",
    "arrest_notes": "Suspect apprehended without resistance at residence."
  }'
```

**Success Response (200):**
```json
{
  "id": 12,
  "full_name": "Roy Earle",
  "status": "arrested",
  "status_display": "Arrested",
  "...": "..."
}
```

**Side Effects:**
- Suspect status updated to `arrested`
- `arrested_at` timestamp set
- Active warrant marked as `executed`
- `SuspectStatusLog` entry created (wanted → arrested)
- Notifications dispatched to assigned Detective and Sergeant

---

### 3.4 Warrantless Arrest (Override)

```bash
curl -X POST http://localhost:8000/api/suspects/12/arrest/ \
  -H "Authorization: Bearer <sergeant_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "arrest_location": "Corner of 5th and Main",
    "arrest_notes": "Suspect caught fleeing crime scene.",
    "warrant_override_justification": "Suspect caught in the act of committing a felony."
  }'
```

The override justification is recorded in the `SuspectStatusLog`
for full audit traceability.

---

## 4. Files Modified

| File | Changes |
|------|---------|
| `backend/suspects/models.py` | Added `SuspectStatusLog` model, `arrested_at` field on `Suspect` |
| `backend/suspects/services.py` | Implemented `issue_arrest_warrant()`, `execute_arrest()`, `transition_status()` |
| `backend/suspects/views.py` | Wired three view actions to service methods with exception handling |
| `backend/suspects/admin.py` | Registered `SuspectStatusLog` in Django admin |
| `backend/core/domain/notifications.py` | Added `warrant_issued` and `suspect_arrested` event types |
| `backend/suspects/migrations/0004_*` | Migration for new model and field |
