# Data Models Report — Key Entities and Design Reasoning

**Author:** Sadegh Sargeran  
**Phase:** First Checkpoint — Backend Data Model Design  
**Date:** February 2026

---

## 1. Overview

This document details every Django model in the system, explains its role, its relationships to other entities, and the reasoning behind its existence. The data model was designed to precisely fulfill the requirements stated in the project document (L.A. Noire Police Department system), without over-engineering or under-delivering.

The backend is split into **6 Django apps**, each representing a bounded domain:

| App        | Domain                | Models                                                                                                              |
| ---------- | --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `core`     | Shared infrastructure | `TimeStampedModel` (abstract), `Notification`                                                                       |
| `accounts` | Users & RBAC          | `Role`, `User`                                                                                                      |
| `cases`    | Case lifecycle        | `Case`, `CaseComplainant`, `CaseWitness`, `CaseStatusLog`                                                           |
| `evidence` | Evidence management   | `Evidence` (base), `TestimonyEvidence`, `BiologicalEvidence`, `VehicleEvidence`, `IdentityEvidence`, `EvidenceFile` |
| `suspects` | Suspect lifecycle     | `Suspect`, `Interrogation`, `Trial`, `BountyTip`, `Bail`                                                            |
| `board`    | Detective Board       | `DetectiveBoard`, `BoardNote`, `BoardItem`, `BoardConnection`                                                       |

---

## 2. App: `core`

### 2.1 `TimeStampedModel` (Abstract)

| Aspect            | Detail                                                                                                                                                                                                                                                                            |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Abstract base model providing `created_at` and `updated_at` timestamp fields.                                                                                                                                                                                                     |
| **Why it exists** | Nearly every entity in the system needs creation and modification timestamps (evidence registration dates, case creation dates, audit trail dates, etc.). Extracting these into an abstract model eliminates repetition across all concrete models and ensures consistent naming. |
| **Relations**     | None — it is abstract and not instantiated as a table.                                                                                                                                                                                                                            |

### 2.2 `Notification`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A notification record sent to a specific user, with an optional generic link to the triggering object.                                                                                                                                                                                                                                                                                        |
| **Why it exists** | The project doc (§4.4) requires that "for each new document and evidence added while a case is being solved, a notification must be sent to the Detective." Notifications are also needed for approval/rejection events (§4.2, §4.4, §4.8). A dedicated model with a `GenericForeignKey` allows any model to trigger a notification without creating separate notification tables per domain. |
| **Key relations** | `recipient → User` (FK); `content_object → any model` (GenericFK via ContentType).                                                                                                                                                                                                                                                                                                            |

---

## 3. App: `accounts`

### 3.1 `Role`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A dynamic, database-driven role definition (name + description + hierarchy level).                                                                                                                                                                                                                                                                                                              |
| **Why it exists** | The project doc (§2.2, §4.1) explicitly requires that "without needing to change the code, the system administrator must be able to add a new role, delete existing roles, or modify them." Hardcoding roles as Python constants or Django groups would violate this requirement. A dedicated `Role` model lets the admin perform full CRUD on roles at runtime through the admin panel or API. |
| **Key fields**    | `name` (unique — the role identifier), `hierarchy_level` (integer encoding the rank's authority: Police Chief > Captain > Sergeant, etc., used for permission checks and workflow routing).                                                                                                                                                                                                     |
| **Relations**     | Reverse FK from `User.role`.                                                                                                                                                                                                                                                                                                                                                                    |

### 3.2 `User`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **What it is**    | Custom user model extending Django's `AbstractUser`, adding `national_id`, `phone_number`, and a `role` FK.                                                                                                                                                                                                                                                                                                                                      |
| **Why it exists** | The project doc (§4.1) requires registration with username, password, email, phone number, full name, and national ID — all unique. Login must work with any one of username / national_id / phone_number / email. Django's default `User` model lacks `national_id` and `phone_number`, and its `email` is not unique by default. A custom `AbstractUser` subclass is the correct Django pattern to add these fields before any migrations run. |
| **Key fields**    | `national_id` (unique, indexed — used for login and cross-referencing suspects), `phone_number` (unique, indexed), `email` (unique).                                                                                                                                                                                                                                                                                                             |
| **Relations**     | `role → Role` (FK, nullable — new users start as "Base User" assigned by admin later).                                                                                                                                                                                                                                                                                                                                                           |

#### Why ForeignKey (single role) instead of ManyToManyField (multiple roles)?

The project document consistently describes each user as holding **one operational role** at a time. Every workflow is written from the perspective of a single role: "the Cadet reviews…", "the Detective identifies suspects…", "the Sergeant interrogates…". Section §4.1 states "the system administrator grants each user the roles they require" — the plural "roles" here refers to **multiple users** each receiving **their** (singular) role, not one user receiving multiple roles simultaneously. No scenario in the document requires a single user to act as both Detective _and_ Sergeant at the same time. Therefore, a simple `ForeignKey` is the accurate, simpler, and more performant mapping. `on_delete=SET_NULL` ensures that if a role is deleted, affected users are not lost — they simply become role-less until the admin reassigns them.

---

## 4. App: `cases`

### 4.1 `Case`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | The central entity — a police case tracking a criminal investigation from creation to closure.                                                                                                                                                                                                                                                                                                                 |
| **Why it exists** | The entire system revolves around cases (§4.2–§4.9). Every other entity (evidence, suspects, interrogations, trials, the detective board) is linked to a case.                                                                                                                                                                                                                                                 |
| **Key fields**    | `title`, `description`, `crime_level` (IntegerChoices 1–4 mapping Level 3 through Critical — the integer value directly serves as the "degree" in the Most-Wanted formula), `status` (16-state TextChoices covering both creation workflows and investigation pipeline), `creation_type` (complaint vs. crime-scene), `rejection_count` (3 rejections → case voided, per §4.2.1), `incident_date`, `location`. |
| **Relations**     | `created_by → User` (PROTECT), `approved_by → User` (for crime-scene workflow, §4.2.2), `assigned_detective/sergeant/captain/judge → User` (track personnel throughout the pipeline). Reverse relations: `complainants`, `witnesses`, `status_logs`, `evidences`, `suspects`, `interrogations`, `trials`, `bounty_tips`, `bails`, `detective_board`.                                                           |

**Design note on `CrimeLevel` integer mapping:** The project doc defines Level 3 as minor (degree 1) up to Critical (degree 4). Using `IntegerChoices` where the DB value _is_ the degree (1, 2, 3, 4) means the Most-Wanted ranking formula (`max(Lj) × max(Di)`) can use `case.crime_level` directly without a lookup table.

### 4.2 `CaseComplainant`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **What it is**    | Junction table linking complainant users to a case, with an approval status.                                                                                                                                                                                                                                                                                                                                             |
| **Why it exists** | §4.2.1 states "a case might have multiple other complainants" and "the information of the complainants will be approved or rejected by the Cadet." A simple FK from Case to a single complainant would not suffice — we need a many-to-many with metadata (is_primary, approval status, reviewed_by). §4.2.2 also says crime-scene cases "initially do not have a complainant, but complainants can gradually be added." |
| **Key fields**    | `is_primary` (marks the original filer of the complaint), `status` (pending / approved / rejected), `reviewed_by` (the Cadet who reviewed).                                                                                                                                                                                                                                                                              |
| **Relations**     | `case → Case` (CASCADE), `user → User` (CASCADE). Unique together on (case, user).                                                                                                                                                                                                                                                                                                                                       |

### 4.3 `CaseWitness`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A witness recorded for a crime-scene case, storing their contact info.                                                                                                                                                                                                                                                                                                 |
| **Why it exists** | §4.2.2 requires that "the phone number and national ID of witnesses are recorded in the case for future follow-ups." Witnesses are **not** necessarily registered system users (they are ordinary bystanders), so we cannot simply FK to `User`. A dedicated model with `full_name`, `phone_number`, and `national_id` stores their contact information independently. |
| **Relations**     | `case → Case` (CASCADE).                                                                                                                                                                                                                                                                                                                                               |

### 4.4 `CaseStatusLog`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Immutable audit trail of every status transition a case undergoes.                                                                                                                                                                                                                                                                                                                                                                                  |
| **Why it exists** | The project doc requires tracking rejections with messages (§4.2.1: "when returning the case to the complainant, it must include an error message written by the Cadet"), and the General Reporting page (§5.7) must show "every approved or rejected report and their specifics." Without an audit log, this history would be lost after each status change. Each row records `from_status`, `to_status`, `changed_by`, and an optional `message`. |
| **Relations**     | `case → Case` (CASCADE), `changed_by → User` (SET_NULL).                                                                                                                                                                                                                                                                                                                                                                                            |

---

## 5. App: `evidence`

Evidence is implemented using **multi-table inheritance** from a shared `Evidence` base. This was chosen because:

- All evidence types share common fields (title, description, registrar, case, registration date) — per §4.3.
- Each sub-type has unique fields that don't apply to others.
- Multi-table inheritance gives each type its own table (clean schema) while allowing queries across all evidence via the base `Evidence` model (needed for the detective board GenericFK and the general reporting page).

### 5.1 `Evidence` (Base)

| Aspect            | Detail                                                                                                                                                                                                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Base evidence record with shared fields + a `evidence_type` discriminator.                                                                                                                                                                                          |
| **Why it exists** | §4.3 states all evidence includes a title, description, registration date, and a registrar. This base captures those universally. For "Other Items" (§4.3.5: "recorded as a title-description record"), the base model alone is sufficient — no child table needed. |
| **Key fields**    | `evidence_type` (discriminator: testimony / biological / vehicle / identity / other), `title`, `description`, `registered_by`.                                                                                                                                      |
| **Relations**     | `case → Case` (CASCADE), `registered_by → User` (PROTECT). Reverse: `files` (EvidenceFile).                                                                                                                                                                         |

### 5.2 `TestimonyEvidence`

| Aspect            | Detail                                                                                                                                                                                                                      |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Child of `Evidence` for witness/local testimonies.                                                                                                                                                                          |
| **Why it exists** | §4.3.1 requires storing "a transcript of the witnesses' statements" as well as images, videos, or audio from locals. The `statement_text` field holds the transcript; attached media goes into related `EvidenceFile` rows. |
| **Key fields**    | `statement_text`.                                                                                                                                                                                                           |

### 5.3 `BiologicalEvidence`

| Aspect            | Detail                                                                                                                                                                                                                                                                                  |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Child of `Evidence` for forensic items (bloodstains, hair, fingerprints).                                                                                                                                                                                                               |
| **Why it exists** | §4.3.2 requires saving biological items with "one or more images" and a forensic result that "is initially empty but can be filled in later" by the Coroner (§3.1.2). The `forensic_result` field starts blank; `verified_by` + `is_verified` track the Coroner's examination workflow. |
| **Key fields**    | `forensic_result`, `verified_by`, `is_verified`.                                                                                                                                                                                                                                        |
| **Relations**     | `verified_by → User` (SET_NULL) — the Coroner who examined it.                                                                                                                                                                                                                          |

### 5.4 `VehicleEvidence`

| Aspect            | Detail                                                                                                                                                                                                                                                           |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Child of `Evidence` for vehicles found at the crime scene.                                                                                                                                                                                                       |
| **Why it exists** | §4.3.3 requires recording `vehicle_model`, `license_plate`, and `color`. It also states: "if a vehicle lacks a license plate, its serial number must be entered" and "the license plate number and the serial number cannot both have a value at the same time." |
| **Key fields**    | `vehicle_model`, `color`, `license_plate`, `serial_number`.                                                                                                                                                                                                      |
| **Constraint**    | A `CheckConstraint` (`vehicle_plate_xor_serial`) enforces the XOR rule at the database level — exactly one of `license_plate` or `serial_number` must be non-empty. This prevents invalid data regardless of which API or admin interface is used.               |

### 5.5 `IdentityEvidence`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **What it is**    | Child of `Evidence` for ID documents found at the scene.                                                                                                                                                                                                                                                                                               |
| **Why it exists** | §4.3.4 requires saving "the full name of the document's owner along with other details of the document in a key-value format." The key-value pairs "do not have a fixed quantity and might even not exist at all." A `JSONField` (`document_details`) perfectly models this dynamic, schema-less structure without needing a separate key-value table. |
| **Key fields**    | `owner_full_name`, `document_details` (JSONField, default=`{}`).                                                                                                                                                                                                                                                                                       |

### 5.6 `EvidenceFile`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | File attachment (image, video, audio, document) for any evidence row.                                                                                                                                                                                                                                       |
| **Why it exists** | Multiple evidence types require file attachments: testimonies need images/videos/audio from locals (§4.3.1), biological evidence needs "one or more images" (§4.3.2). A single reusable file model with a `file_type` discriminator and FK to the base `Evidence` avoids duplicating upload logic per type. |
| **Key fields**    | `file` (FileField), `file_type` (image/video/audio/document), `caption`.                                                                                                                                                                                                                                    |
| **Relations**     | `evidence → Evidence` (CASCADE).                                                                                                                                                                                                                                                                            |

---

## 6. App: `suspects`

### 6.1 `Suspect`

| Aspect                  | Detail                                                                                                                                                                                                                                                                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**          | Links an individual to a case as a suspect, tracking their status and wanted duration.                                                                                                                                                                                                                                                            |
| **Why it exists**       | §4.4 and §4.5 require the Detective to declare suspects, the Sergeant to approve them, and the system to track their status (wanted / arrested / under interrogation / under trial / convicted / acquitted / released on bail). §4.7 requires tracking "wanted since" to determine Most-Wanted status (>30 days) and computing the ranking score. |
| **Key fields**          | `full_name`, `national_id` (indexed — used to aggregate across cases for Most-Wanted ranking), `photo` (for the Most Wanted page, §4.7), `status` (choices covering the full lifecycle), `wanted_since` (auto-set, used in days calculation).                                                                                                     |
| **Relations**           | `case → Case` (CASCADE), `user → User` (optional FK — suspect may or may not be a registered user), `identified_by → User` (PROTECT — the detective), `approved_by_sergeant → User`.                                                                                                                                                              |
| **Computed properties** | `days_wanted` — days since identification. `is_most_wanted` — True if wanted > 30 days (§4.7). `most_wanted_score` — `max(Lj) × max(Di)` formula per §4.7 Note 1 (aggregates across all Suspect rows with the same `national_id`). `reward_amount` — bounty formula per §4.7 Note 2.                                                              |

**Design note:** A person may be a suspect in multiple cases; each combination is a separate `Suspect` row. The Most-Wanted ranking formula requires cross-case aggregation (max days across open cases × max crime degree across all cases) — this is done by grouping on `national_id`.

### 6.2 `Interrogation`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Records a joint interrogation by Detective and Sergeant, including their guilt-probability scores.                                                                                                                                                                                                          |
| **Why it exists** | §4.5 states that after arrest, "both the Sergeant and the Detective assign a probability of the suspect's guilt from 1 to 10" and "their scores are then sent to the Captain." A model is needed to persist these scores and link them to the specific case and suspect. Validators enforce the 1–10 range. |
| **Key fields**    | `detective_guilt_score` (1–10), `sergeant_guilt_score` (1–10), `notes`.                                                                                                                                                                                                                                     |
| **Relations**     | `suspect → Suspect` (CASCADE), `case → Case` (CASCADE), `detective → User` (PROTECT), `sergeant → User` (PROTECT).                                                                                                                                                                                          |

### 6.3 `Trial`

| Aspect            | Detail                                                                                                                                                                                                                                                                                       |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Court trial record with the Judge's verdict and (if guilty) punishment details.                                                                                                                                                                                                              |
| **Why it exists** | §4.6 requires that "the final verdict of guilty or innocent is logged by the Judge, and if guilty, the punishment is recorded by them with a title and description." The Judge needs access to the entire case file — the Trial model links to both the Suspect and Case to facilitate this. |
| **Key fields**    | `verdict` (guilty / innocent), `punishment_title`, `punishment_description` (both populated only on guilty verdict).                                                                                                                                                                         |
| **Relations**     | `suspect → Suspect` (CASCADE), `case → Case` (CASCADE), `judge → User` (PROTECT).                                                                                                                                                                                                            |

### 6.4 `BountyTip`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A citizen-submitted tip about a suspect or case, with a multi-stage review pipeline.                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Why it exists** | §4.8 defines a complete workflow: (1) citizen submits info → (2) police officer reviews → (3) detective verifies → (4) citizen receives a unique ID to claim their bounty. The model tracks every stage: `status` (pending → officer_reviewed → verified / rejected), who reviewed and verified, the generated `unique_code`, and the reward amount. §4.8 also requires that "all police ranks must be able to enter the person's national ID and unique code to view the bounty amount." |
| **Key fields**    | `information` (the submitted text), `status` (pipeline stage), `unique_code` (generated on verification — the reward claim ID), `reward_amount`, `is_claimed`.                                                                                                                                                                                                                                                                                                                            |
| **Relations**     | `suspect → Suspect` (optional), `case → Case` (optional), `informant → User` (the citizen), `reviewed_by → User` (officer), `verified_by → User` (detective).                                                                                                                                                                                                                                                                                                                             |

### 6.5 `Bail`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                    |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | Bail/fine payment record for a suspect.                                                                                                                                                                                                                                                                                                                                   |
| **Why it exists** | §4.9 (optional feature) states that "suspects of Level 2 and Level 3 crimes, as well as Level 3 criminals (pending the Sergeant's approval), can be released from custody by paying bail and fines. The amount is determined by the Sergeant." A model is needed to store the sergeant-determined amount, track payment status, and record the payment gateway reference. |
| **Key fields**    | `amount`, `is_paid`, `payment_reference` (gateway transaction ID), `paid_at`.                                                                                                                                                                                                                                                                                             |
| **Relations**     | `suspect → Suspect` (CASCADE), `case → Case` (CASCADE), `approved_by → User` (PROTECT — the Sergeant).                                                                                                                                                                                                                                                                    |

---

## 7. App: `board`

### 7.1 `DetectiveBoard`

| Aspect            | Detail                                                                                                                                                                                                                                                    |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A visual workspace — one per case — where the detective arranges evidence and notes.                                                                                                                                                                      |
| **Why it exists** | §4.4 and §5.4 describe the Detective Board as a canvas where "documents and evidence are placed anywhere the Detective desires" with drag-and-drop positioning and red-line connections. A OneToOne link to Case ensures each case has exactly one board. |
| **Relations**     | `case → Case` (OneToOne, CASCADE), `detective → User` (CASCADE).                                                                                                                                                                                          |

### 7.2 `BoardNote`

| Aspect            | Detail                                                                                                                                                                                                                                                                                   |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A free-form note that can be pinned to the detective board.                                                                                                                                                                                                                              |
| **Why it exists** | §5.4 says the board "must contain a number of documents or notes." Evidence items already exist as `Evidence` objects, but detectives also need to write their own reasoning, hypotheses, or annotations. `BoardNote` provides this distinct "note" entity, separate from case evidence. |
| **Key fields**    | `title`, `content`.                                                                                                                                                                                                                                                                      |
| **Relations**     | `board → DetectiveBoard` (CASCADE), `created_by → User`.                                                                                                                                                                                                                                 |

### 7.3 `BoardItem`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                                                      |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A positioned element on the board canvas, linking via GenericForeignKey to any content (Evidence or BoardNote).                                                                                                                                                                                                                                                             |
| **Why it exists** | §5.4 requires drag-and-drop placement — each item needs X/Y coordinates. Items can be either existing evidence or detective notes. Using a `GenericForeignKey` (via Django's `ContentType` framework) allows a single item table to reference any model type without separate join tables per type. This also makes the board extensible if new item types are added later. |
| **Key fields**    | `position_x`, `position_y` (float — pixel or percentage coords, frontend decides the unit).                                                                                                                                                                                                                                                                                 |
| **Relations**     | `board → DetectiveBoard` (CASCADE), `content_object → any model` (GenericFK).                                                                                                                                                                                                                                                                                               |

### 7.4 `BoardConnection`

| Aspect            | Detail                                                                                                                                                                                                                                                                                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **What it is**    | A "red line" connecting two `BoardItem` nodes on the detective board.                                                                                                                                                                                                                                                                       |
| **Why it exists** | §4.4 and §5.4 require the detective to "connect related documents with a red line" and that "the lines between documents must also be addable and removable." This model stores each connection as a pair of `BoardItem` FKs with a unique constraint to prevent duplicate lines. An optional `label` field allows annotations on the line. |
| **Relations**     | `board → DetectiveBoard` (CASCADE), `from_item → BoardItem`, `to_item → BoardItem`. Unique together on (from_item, to_item).                                                                                                                                                                                                                |

---

## 8. Relationship Summary Diagram (textual)

```
User ──FK──> Role

Case ──FK──> User  (created_by, approved_by, detective, sergeant, captain, judge)
CaseComplainant ──FK──> Case, User
CaseWitness ──FK──> Case
CaseStatusLog ──FK──> Case, User

Evidence ──FK──> Case, User (registrar)
  ├── TestimonyEvidence (inherits Evidence)
  ├── BiologicalEvidence (inherits Evidence) ──FK──> User (coroner)
  ├── VehicleEvidence (inherits Evidence)
  └── IdentityEvidence (inherits Evidence)
EvidenceFile ──FK──> Evidence

Suspect ──FK──> Case, User (optional link, identified_by, sergeant)
Interrogation ──FK──> Suspect, Case, User (detective), User (sergeant)
Trial ──FK──> Suspect, Case, User (judge)
BountyTip ──FK──> Suspect, Case, User (informant, reviewer, verifier)
Bail ──FK──> Suspect, Case, User (sergeant)

DetectiveBoard ──OneToOne──> Case, FK──> User (detective)
BoardNote ──FK──> DetectiveBoard, User
BoardItem ──FK──> DetectiveBoard, GenericFK──> (Evidence | BoardNote)
BoardConnection ──FK──> DetectiveBoard, BoardItem (from), BoardItem (to)

Notification ──FK──> User (recipient), GenericFK──> any model
```

---

## 9. Design Decisions Summary

| Decision                                   | Reasoning                                                                                                                                                                                            |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ForeignKey (single role) for User→Role** | The project doc treats each user as holding one role at a time. No scenario requires simultaneous multi-role. FK is simpler, faster, and accurate to requirements.                                   |
| **Multi-table inheritance for Evidence**   | All types share base fields; each has unique additions. Allows querying all evidence uniformly (needed for board GenericFK and reporting) while keeping type-specific data in clean separate tables. |
| **CheckConstraint on VehicleEvidence**     | Enforces the license-plate XOR serial-number rule (§4.3.3) at the DB level, preventing invalid data regardless of entry point (API, admin, shell).                                                   |
| **JSONField for IdentityEvidence**         | Dynamic key-value pairs with no fixed schema (§4.3.4). A separate Key-Value table would add complexity with no benefit since no cross-document querying on individual keys is needed.                |
| **GenericForeignKey on BoardItem**         | The board must pin both Evidence and BoardNote objects. GFK avoids separate item tables per content type and makes the board extensible.                                                             |
| **CaseStatusLog as immutable audit trail** | Rejection messages, approval history, and status transitions must be preserved for the General Reporting page (§5.7) and for the "3 rejections → voided" logic.                                      |
| **Suspect as a per-case record**           | A person can be a suspect in multiple cases. The Most-Wanted formula aggregates across cases by `national_id`. Per-case rows let each case track its own suspect status independently.               |
| **BountyTip with multi-stage status**      | The bounty workflow (§4.8) has three review stages. Modeling this as a status field with reviewer/verifier FKs keeps the pipeline in a single table rather than splitting across multiple models.    |
| **TimeStampedModel abstract base**         | Eliminates repetitive `created_at`/`updated_at` field declarations across ~20 models.                                                                                                                |

---

_Report prepared by Sadegh Sargeran._
