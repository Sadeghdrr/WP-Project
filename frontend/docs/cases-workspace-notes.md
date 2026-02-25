# Cases Workspace — Implementation Notes

## Endpoints Used

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/cases/cases/` | GET | List cases with filters |
| `/api/cases/cases/` | POST | Create case (complaint or crime scene) |
| `/api/cases/cases/{id}/` | GET | Case detail |
| `/api/cases/cases/{id}/` | PATCH | Update case metadata |
| `/api/cases/cases/{id}/submit/` | POST | Submit complaint for review |
| `/api/cases/cases/{id}/resubmit/` | POST | Resubmit returned complaint |
| `/api/cases/cases/{id}/cadet-review/` | POST | Cadet approve/reject |
| `/api/cases/cases/{id}/officer-review/` | POST | Officer approve/reject |
| `/api/cases/cases/{id}/approve-crime-scene/` | POST | Approve crime scene case |
| `/api/cases/cases/{id}/declare-suspects/` | POST | Detective declares suspects |
| `/api/cases/cases/{id}/sergeant-review/` | POST | Sergeant approve/reject |
| `/api/cases/cases/{id}/forward-judiciary/` | POST | Forward to judiciary |
| `/api/cases/cases/{id}/transition/` | POST | Generic state transition |
| `/api/cases/cases/{id}/assign-detective/` | POST | Assign detective |
| `/api/cases/cases/{id}/assign-sergeant/` | POST | Assign sergeant |
| `/api/cases/cases/{id}/assign-captain/` | POST | Assign captain |
| `/api/cases/cases/{id}/assign-judge/` | POST | Assign judge |
| `/api/cases/cases/{id}/status-log/` | GET | Status audit trail |
| `/api/cases/cases/{id}/calculations/` | GET | Case reward calculations |

## Status Model / Frontend Mapping

Status lifecycle mirrors backend `CaseStatus` choices:

### Complaint Path
```
complaint_registered → cadet_review → officer_review → open
                         ↓ reject            ↓ reject
               returned_to_complainant   returned_to_cadet
                         ↓ 3 rejections
                       voided
```

### Crime Scene Path
```
pending_approval → open (or auto-open if Police Chief created)
```

### Investigation Pipeline (after OPEN)
```
open → investigation → suspect_identified → sergeant_review → arrest_ordered
  → interrogation → captain_review → [chief_review] → judiciary → closed
```

## Action Visibility Logic

Actions shown in the workflow panel are determined by:
1. **Current case status** — each status has a fixed set of possible actions
2. **User permissions** — actions are filtered by `permissionSet.has(permission)`
3. **Terminal states** — voided/closed cases show "no actions available"

Permission mapping follows backend `ALLOWED_TRANSITIONS`:
- `cases.add_case` → submit/resubmit (complainant)
- `cases.can_review_complaint` → cadet review actions
- `cases.can_approve_case` → officer review, crime scene approval
- `cases.can_assign_detective` → assign detective
- `cases.can_change_case_status` → investigation pipeline transitions
- `cases.can_forward_to_judiciary` → forward to judiciary
- `cases.can_approve_critical_case` → escalate critical cases to chief

## Deferred Pieces

- **File Complaint form** — create complaint with form fields (placeholder page exists)
- **Crime Scene form** — create crime scene with witness entry (placeholder page exists)
- **Inline case editing** — PATCH case metadata from detail page
- **Assignment user picker** — select users by role for assignment (needs user list endpoint with role filter)
- **Complainant management** — add/review complainants from detail page
- **Witness management** — add witnesses from detail page
- **Case deletion** — admin-only delete action
- **Full report view** — `/api/cases/cases/{id}/report/` for judiciary
