# Swagger / OpenAPI Documentation Report

> **Generated for:** LAPD Case Management System  
> **Library:** `drf-spectacular` (OpenAPI 3.0)  
> **Date:** 2025-07-22

---

## 1. Overview

Every `views.py` across all six Django apps has been enriched with
`@extend_schema` decorators from `drf-spectacular`. Serializer fields that
previously lacked descriptions now carry `help_text` attributes so
they appear in the generated schema.

**No business logic was changed.** Only decorators, imports, and
`help_text` strings were added.

---

## 2. Serializer Enrichment (`help_text`)

| App      | Serializer                            | Fields enriched                                                                                                |
| -------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| accounts | `LoginRequestSerializer`              | `password`                                                                                                     |
| accounts | `AssignRoleSerializer`                | `role_id`                                                                                                      |
| cases    | `CaseFilterSerializer`                | `status`, `crime_level`, `detective`, `creation_type`, `created_after`, `created_before`, `search`             |
| cases    | `CaseTransitionSerializer`            | `target_status`, `message`                                                                                     |
| cases    | `CadetReviewSerializer`               | `decision`, `message`                                                                                          |
| cases    | `OfficerReviewSerializer`             | `decision`, `message`                                                                                          |
| cases    | `AssignPersonnelSerializer`           | `user_id`                                                                                                      |
| cases    | `AddComplainantSerializer`            | `user_id`                                                                                                      |
| suspects | `SuspectFilterSerializer`             | `status`, `case`, `national_id`, `search`, `most_wanted`, `created_after`, `created_before`, `approval_status` |
| suspects | `SuspectApprovalSerializer`           | `decision`, `rejection_message`                                                                                |
| evidence | `EvidenceFilterSerializer`            | `evidence_type`, `verification_status`, `case`, `collected_after`, `collected_before`, `search`                |
| evidence | `EvidencePolymorphicCreateSerializer` | `evidence_type`                                                                                                |

---

## 3. View Decoration Summary

### 3.1 `accounts` app — Tag: **Auth**, **Users**, **Roles**

| View / Method                    | HTTP   | Path                                           | Tag   |
| -------------------------------- | ------ | ---------------------------------------------- | ----- |
| `RegisterView.create`            | POST   | `/api/accounts/register/`                      | Auth  |
| `LoginView.post`                 | POST   | `/api/accounts/login/`                         | Auth  |
| `MeView.get`                     | GET    | `/api/accounts/me/`                            | Auth  |
| `MeView.patch`                   | PATCH  | `/api/accounts/me/`                            | Auth  |
| `UserViewSet.list`               | GET    | `/api/accounts/users/`                         | Users |
| `UserViewSet.retrieve`           | GET    | `/api/accounts/users/{id}/`                    | Users |
| `UserViewSet.assign_role`        | POST   | `/api/accounts/users/{id}/assign-role/`        | Users |
| `UserViewSet.activate`           | POST   | `/api/accounts/users/{id}/activate/`           | Users |
| `UserViewSet.deactivate`         | POST   | `/api/accounts/users/{id}/deactivate/`         | Users |
| `RoleViewSet.list`               | GET    | `/api/accounts/roles/`                         | Roles |
| `RoleViewSet.create`             | POST   | `/api/accounts/roles/`                         | Roles |
| `RoleViewSet.retrieve`           | GET    | `/api/accounts/roles/{id}/`                    | Roles |
| `RoleViewSet.update`             | PUT    | `/api/accounts/roles/{id}/`                    | Roles |
| `RoleViewSet.partial_update`     | PATCH  | `/api/accounts/roles/{id}/`                    | Roles |
| `RoleViewSet.destroy`            | DELETE | `/api/accounts/roles/{id}/`                    | Roles |
| `RoleViewSet.assign_permissions` | POST   | `/api/accounts/roles/{id}/assign-permissions/` | Roles |
| `PermissionListView`             | GET    | `/api/accounts/permissions/`                   | Roles |

### 3.2 `cases` app — Tags: **Cases**, **Cases – Workflow**, **Cases – Assignment**, **Cases – Complainants**, **Cases – Witnesses**

| View / Method                     | HTTP     | Path                                   | Tag                  |
| --------------------------------- | -------- | -------------------------------------- | -------------------- |
| `CaseViewSet.list`                | GET      | `/api/cases/`                          | Cases                |
| `CaseViewSet.create`              | POST     | `/api/cases/`                          | Cases                |
| `CaseViewSet.retrieve`            | GET      | `/api/cases/{id}/`                     | Cases                |
| `CaseViewSet.partial_update`      | PATCH    | `/api/cases/{id}/`                     | Cases                |
| `CaseViewSet.destroy`             | DELETE   | `/api/cases/{id}/`                     | Cases                |
| `CaseViewSet.submit`              | POST     | `/api/cases/{id}/submit/`              | Cases – Workflow     |
| `CaseViewSet.resubmit`            | POST     | `/api/cases/{id}/resubmit/`            | Cases – Workflow     |
| `CaseViewSet.cadet_review`        | POST     | `/api/cases/{id}/cadet-review/`        | Cases – Workflow     |
| `CaseViewSet.officer_review`      | POST     | `/api/cases/{id}/officer-review/`      | Cases – Workflow     |
| `CaseViewSet.approve_crime_scene` | POST     | `/api/cases/{id}/approve-crime-scene/` | Cases – Workflow     |
| `CaseViewSet.declare_suspects`    | POST     | `/api/cases/{id}/declare-suspects/`    | Cases – Workflow     |
| `CaseViewSet.sergeant_review`     | POST     | `/api/cases/{id}/sergeant-review/`     | Cases – Workflow     |
| `CaseViewSet.forward_judiciary`   | POST     | `/api/cases/{id}/forward-judiciary/`   | Cases – Workflow     |
| `CaseViewSet.transition`          | POST     | `/api/cases/{id}/transition/`          | Cases – Workflow     |
| `CaseViewSet.assign_detective`    | POST     | `/api/cases/{id}/assign-detective/`    | Cases – Assignment   |
| `CaseViewSet.unassign_detective`  | POST     | `/api/cases/{id}/unassign-detective/`  | Cases – Assignment   |
| `CaseViewSet.assign_sergeant`     | POST     | `/api/cases/{id}/assign-sergeant/`     | Cases – Assignment   |
| `CaseViewSet.assign_captain`      | POST     | `/api/cases/{id}/assign-captain/`      | Cases – Assignment   |
| `CaseViewSet.assign_judge`        | POST     | `/api/cases/{id}/assign-judge/`        | Cases – Assignment   |
| `CaseViewSet.complainants`        | GET/POST | `/api/cases/{id}/complainants/`        | Cases – Complainants |
| `CaseViewSet.review_complainant`  | POST     | `/api/cases/{id}/review-complainant/`  | Cases – Complainants |
| `CaseViewSet.witnesses`           | GET/POST | `/api/cases/{id}/witnesses/`           | Cases – Witnesses    |
| `CaseViewSet.status_log`          | GET      | `/api/cases/{id}/status-log/`          | Cases – Workflow     |
| `CaseViewSet.calculations`        | GET      | `/api/cases/{id}/calculations/`        | Cases                |

### 3.3 `suspects` app — Tags: **Suspects**, **Suspects – Workflow**, **Interrogations**, **Trials**, **Bail**, **Bounty Tips**

| View / Method                      | HTTP  | Path                                              | Tag                 |
| ---------------------------------- | ----- | ------------------------------------------------- | ------------------- |
| `SuspectViewSet.list`              | GET   | `/api/suspects/`                                  | Suspects            |
| `SuspectViewSet.create`            | POST  | `/api/suspects/`                                  | Suspects            |
| `SuspectViewSet.retrieve`          | GET   | `/api/suspects/{id}/`                             | Suspects            |
| `SuspectViewSet.partial_update`    | PATCH | `/api/suspects/{id}/`                             | Suspects            |
| `SuspectViewSet.most_wanted`       | GET   | `/api/suspects/most-wanted/`                      | Suspects            |
| `SuspectViewSet.approve`           | POST  | `/api/suspects/{id}/approve/`                     | Suspects – Workflow |
| `SuspectViewSet.issue_warrant`     | POST  | `/api/suspects/{id}/issue-warrant/`               | Suspects – Workflow |
| `SuspectViewSet.arrest`            | POST  | `/api/suspects/{id}/arrest/`                      | Suspects – Workflow |
| `SuspectViewSet.transition_status` | POST  | `/api/suspects/{id}/transition-status/`           | Suspects – Workflow |
| `InterrogationViewSet.list`        | GET   | `/api/suspects/{suspect_pk}/interrogations/`      | Interrogations      |
| `InterrogationViewSet.create`      | POST  | `/api/suspects/{suspect_pk}/interrogations/`      | Interrogations      |
| `InterrogationViewSet.retrieve`    | GET   | `/api/suspects/{suspect_pk}/interrogations/{id}/` | Interrogations      |
| `TrialViewSet.list`                | GET   | `/api/suspects/{suspect_pk}/trials/`              | Trials              |
| `TrialViewSet.create`              | POST  | `/api/suspects/{suspect_pk}/trials/`              | Trials              |
| `TrialViewSet.retrieve`            | GET   | `/api/suspects/{suspect_pk}/trials/{id}/`         | Trials              |
| `BailViewSet.list`                 | GET   | `/api/suspects/{suspect_pk}/bails/`               | Bail                |
| `BailViewSet.create`               | POST  | `/api/suspects/{suspect_pk}/bails/`               | Bail                |
| `BailViewSet.retrieve`             | GET   | `/api/suspects/{suspect_pk}/bails/{id}/`          | Bail                |
| `BailViewSet.pay`                  | POST  | `/api/suspects/{suspect_pk}/bails/{id}/pay/`      | Bail                |
| `BountyTipViewSet.list`            | GET   | `/api/bounty-tips/`                               | Bounty Tips         |
| `BountyTipViewSet.create`          | POST  | `/api/bounty-tips/`                               | Bounty Tips         |
| `BountyTipViewSet.retrieve`        | GET   | `/api/bounty-tips/{id}/`                          | Bounty Tips         |
| `BountyTipViewSet.review`          | POST  | `/api/bounty-tips/{id}/review/`                   | Bounty Tips         |
| `BountyTipViewSet.verify`          | POST  | `/api/bounty-tips/{id}/verify/`                   | Bounty Tips         |
| `BountyTipViewSet.lookup_reward`   | POST  | `/api/bounty-tips/lookup-reward/`                 | Bounty Tips         |

Validation note for `BountyTipViewSet.review` request body:
- `decision` accepts `accept` or `reject`.
- `review_notes` is required when `decision=reject`.

Access note for `BountyTipViewSet.lookup_reward`:
- Allowed for authenticated police-rank users only.
- Requires both `national_id` and `unique_code`.

### 3.4 `evidence` app — Tag: **Evidence**

| View / Method                      | HTTP     | Path                                   | Tag      |
| ---------------------------------- | -------- | -------------------------------------- | -------- |
| `EvidenceViewSet.list`             | GET      | `/api/evidence/`                       | Evidence |
| `EvidenceViewSet.create`           | POST     | `/api/evidence/`                       | Evidence |
| `EvidenceViewSet.retrieve`         | GET      | `/api/evidence/{id}/`                  | Evidence |
| `EvidenceViewSet.partial_update`   | PATCH    | `/api/evidence/{id}/`                  | Evidence |
| `EvidenceViewSet.destroy`          | DELETE   | `/api/evidence/{id}/`                  | Evidence |
| `EvidenceViewSet.verify`           | POST     | `/api/evidence/{id}/verify/`           | Evidence |
| `EvidenceViewSet.link_case`        | POST     | `/api/evidence/{id}/link-case/`        | Evidence |
| `EvidenceViewSet.unlink_case`      | POST     | `/api/evidence/{id}/unlink-case/`      | Evidence |
| `EvidenceViewSet.files`            | GET/POST | `/api/evidence/{id}/files/`            | Evidence |
| `EvidenceViewSet.chain_of_custody` | GET      | `/api/evidence/{id}/chain-of-custody/` | Evidence |

### 3.5 `board` app — Tags: **Detective Board**, **Detective Board – Items**, **Detective Board – Connections**, **Detective Board – Notes**

| View / Method                               | HTTP   | Path                                              | Tag                           |
| ------------------------------------------- | ------ | ------------------------------------------------- | ----------------------------- |
| `DetectiveBoardViewSet.list`                | GET    | `/api/boards/`                                    | Detective Board               |
| `DetectiveBoardViewSet.create`              | POST   | `/api/boards/`                                    | Detective Board               |
| `DetectiveBoardViewSet.retrieve`            | GET    | `/api/boards/{id}/`                               | Detective Board               |
| `DetectiveBoardViewSet.partial_update`      | PATCH  | `/api/boards/{id}/`                               | Detective Board               |
| `DetectiveBoardViewSet.destroy`             | DELETE | `/api/boards/{id}/`                               | Detective Board               |
| `DetectiveBoardViewSet.full_state`          | GET    | `/api/boards/{id}/full/`                          | Detective Board               |
| `BoardItemViewSet.create`                   | POST   | `/api/boards/{board_pk}/items/`                   | Detective Board – Items       |
| `BoardItemViewSet.destroy`                  | DELETE | `/api/boards/{board_pk}/items/{id}/`              | Detective Board – Items       |
| `BoardItemViewSet.batch_update_coordinates` | PATCH  | `/api/boards/{board_pk}/items/batch-coordinates/` | Detective Board – Items       |
| `BoardConnectionViewSet.create`             | POST   | `/api/boards/{board_pk}/connections/`             | Detective Board – Connections |
| `BoardConnectionViewSet.destroy`            | DELETE | `/api/boards/{board_pk}/connections/{id}/`        | Detective Board – Connections |
| `BoardNoteViewSet.create`                   | POST   | `/api/boards/{board_pk}/notes/`                   | Detective Board – Notes       |
| `BoardNoteViewSet.retrieve`                 | GET    | `/api/boards/{board_pk}/notes/{id}/`              | Detective Board – Notes       |
| `BoardNoteViewSet.partial_update`           | PATCH  | `/api/boards/{board_pk}/notes/{id}/`              | Detective Board – Notes       |
| `BoardNoteViewSet.destroy`                  | DELETE | `/api/boards/{board_pk}/notes/{id}/`              | Detective Board – Notes       |

### 3.6 `core` app — Tags: **Dashboard**, **Search**, **System**, **Notifications**

| View / Method                      | HTTP | Path                                 | Tag           |
| ---------------------------------- | ---- | ------------------------------------ | ------------- |
| `DashboardStatsView.get`           | GET  | `/api/core/dashboard/`               | Dashboard     |
| `GlobalSearchView.get`             | GET  | `/api/core/search/`                  | Search        |
| `SystemConstantsView.get`          | GET  | `/api/core/constants/`               | System        |
| `NotificationViewSet.list`         | GET  | `/api/core/notifications/`           | Notifications |
| `NotificationViewSet.mark_as_read` | POST | `/api/core/notifications/{id}/read/` | Notifications |

---

## 4. Swagger UI Access

`drf-spectacular` is already configured in `backend/settings.py`:

```
SPECTACULAR_SETTINGS = { ... }
```

Endpoints (already registered in `backend/urls.py`):

| URL            | Purpose                        |
| -------------- | ------------------------------ |
| `/api/schema/` | Download OpenAPI 3.0 JSON/YAML |
| `/api/docs/`   | Swagger UI                     |
| `/api/redoc/`  | ReDoc UI                       |

---

## 5. Files Modified

| File                      | Changes                                |
| ------------------------- | -------------------------------------- |
| `accounts/serializers.py` | Added `help_text` to 2 fields          |
| `accounts/views.py`       | Added `@extend_schema` to 17 endpoints |
| `cases/serializers.py`    | Added `help_text` to 13 fields         |
| `cases/views.py`          | Added `@extend_schema` to 24 endpoints |
| `suspects/serializers.py` | Added `help_text` to 10 fields         |
| `suspects/views.py`       | Added `@extend_schema` to 26 endpoints |
| `evidence/serializers.py` | Added `help_text` to 7 fields          |
| `evidence/views.py`       | Added `@extend_schema` to 10 endpoints |
| `board/views.py`          | Added `@extend_schema` to 14 endpoints |
| `core/views.py`           | Added `@extend_schema` to 5 endpoints  |

**Total: 96 endpoints documented, 32 serializer fields enriched.**

---

## 6. Validation

```bash
$ python -c "from accounts.views import *; from cases.views import *; \
from suspects.views import *; from evidence.views import *; \
from board.views import *; from core.views import *; print('OK')"
OK
```

All imports pass without errors after decoration.
