"""
Permissions Constants — **Single Source of Truth**

Every permission referenced in code (views, serializers, ``setup_rbac``,
DRF permission classes) MUST use one of the constants defined here.

Organisation
------------
- **Standard CRUD** permissions follow Django's auto-generated naming:
  ``<action>_<model_lowercase>``. They are listed here for reference so
  that the ``setup_rbac`` command can map them to roles without typos.

- **Custom workflow** permissions are constants that map to codenames
  registered via each model's ``Meta.permissions`` tuple. Adding a new
  custom permission requires:
    1. Add the constant below.
    2. Add the ``(codename, description)`` to the related model's
       ``Meta.permissions``.
    3. Run ``makemigrations`` + ``migrate`` to insert it into Django's
       ``auth_permission`` table.
    4. Add the constant to the appropriate role lists in ``setup_rbac``.

All constants store the **codename only** (no ``app_label.`` prefix).
The ``setup_rbac`` command resolves them to full
``app_label.codename`` via ``Permission.objects.get(codename=...)``.
"""


# ════════════════════════════════════════════════════════════════════
#  ACCOUNTS APP — Standard CRUD
# ════════════════════════════════════════════════════════════════════

class AccountsPerms:
    """Standard CRUD permissions for accounts models."""

    # Role
    VIEW_ROLE = "view_role"
    ADD_ROLE = "add_role"
    CHANGE_ROLE = "change_role"
    DELETE_ROLE = "delete_role"

    # User
    VIEW_USER = "view_user"
    ADD_USER = "add_user"
    CHANGE_USER = "change_user"
    DELETE_USER = "delete_user"

    # ── Custom workflow permissions ─────────────────────────────────
    CAN_MANAGE_USERS = "can_manage_users"
    """Admin-level user management (activate, deactivate, assign roles)."""


# ════════════════════════════════════════════════════════════════════
#  CASES APP — Standard CRUD + Custom Workflow
# ════════════════════════════════════════════════════════════════════

class CasesPerms:
    """Standard + custom permissions for the cases app."""

    # ── Case — standard CRUD ────────────────────────────────────────
    VIEW_CASE = "view_case"
    ADD_CASE = "add_case"
    CHANGE_CASE = "change_case"
    DELETE_CASE = "delete_case"

    # ── CaseComplainant — standard CRUD ─────────────────────────────
    VIEW_CASECOMPLAINANT = "view_casecomplainant"
    ADD_CASECOMPLAINANT = "add_casecomplainant"
    CHANGE_CASECOMPLAINANT = "change_casecomplainant"
    DELETE_CASECOMPLAINANT = "delete_casecomplainant"

    # ── CaseWitness — standard CRUD ─────────────────────────────────
    VIEW_CASEWITNESS = "view_casewitness"
    ADD_CASEWITNESS = "add_casewitness"
    CHANGE_CASEWITNESS = "change_casewitness"
    DELETE_CASEWITNESS = "delete_casewitness"

    # ── CaseStatusLog — standard CRUD ───────────────────────────────
    VIEW_CASESTATUSLOG = "view_casestatuslog"
    ADD_CASESTATUSLOG = "add_casestatuslog"
    CHANGE_CASESTATUSLOG = "change_casestatuslog"
    DELETE_CASESTATUSLOG = "delete_casestatuslog"

    # ── Custom workflow permissions ─────────────────────────────────
    CAN_REVIEW_COMPLAINT = "can_review_complaint"
    """Cadet reviews incoming complaints and forwards/returns them."""

    CAN_APPROVE_CASE = "can_approve_case"
    """Officer / superior approves a case after cadet review or crime-scene report."""

    CAN_ASSIGN_DETECTIVE = "can_assign_detective"
    """Assign a detective to investigate the case."""

    CAN_CHANGE_CASE_STATUS = "can_change_case_status"
    """Transition a case through workflow statuses (beyond normal change_case)."""

    CAN_FORWARD_TO_JUDICIARY = "can_forward_to_judiciary"
    """Captain / Police Chief forwards a solved case to the judiciary for trial."""

    CAN_APPROVE_CRITICAL_CASE = "can_approve_critical_case"
    """Police Chief approves critical-level cases that require chief-level sign-off."""

    # ── Scope permissions (data-visibility tiers) ───────────────────
    CAN_SCOPE_ALL_CASES = "can_scope_all_cases"
    """Unrestricted case visibility (Captain, Chief, Admin)."""

    CAN_SCOPE_SUPERVISED_CASES = "can_scope_supervised_cases"
    """See cases assigned to this user as sergeant, plus cases with detectives."""

    CAN_SCOPE_ASSIGNED_CASES = "can_scope_assigned_cases"
    """See only cases assigned to this user as detective."""

    CAN_SCOPE_OFFICER_CASES = "can_scope_officer_cases"
    """See cases past the complaint-screening phase."""

    CAN_SCOPE_COMPLAINT_QUEUE = "can_scope_complaint_queue"
    """See only early-stage complaint cases."""

    CAN_SCOPE_JUDICIARY_CASES = "can_scope_judiciary_cases"
    """See only judiciary/closed cases assigned to this judge."""

    CAN_SCOPE_OWN_CASES = "can_scope_own_cases"
    """See only cases where the user is a complainant or creator."""

    CAN_SCOPE_CORONER_CASES = "can_scope_coroner_cases"
    """See cases containing unverified biological evidence (Coroner)."""

    # ── Workflow guard permissions ──────────────────────────────────
    CAN_CREATE_CRIME_SCENE = "can_create_crime_scene"
    """Allowed to create a crime-scene case (Officer and above)."""

    CAN_AUTO_APPROVE_CRIME_SCENE = "can_auto_approve_crime_scene"
    """Crime-scene cases auto-open on creation (Police Chief)."""

    CAN_VIEW_CASE_REPORT = "can_view_case_report"
    """Access the full aggregated case report."""

    # ── Assignment capability permissions ───────────────────────────
    CAN_BE_ASSIGNED_DETECTIVE = "can_be_assigned_detective"
    """User can be assigned to a case as detective."""

    CAN_BE_ASSIGNED_SERGEANT = "can_be_assigned_sergeant"
    """User can be assigned to a case as sergeant."""

    CAN_BE_ASSIGNED_CAPTAIN = "can_be_assigned_captain"
    """User can be assigned to a case as captain."""

    CAN_BE_ASSIGNED_JUDGE = "can_be_assigned_judge"
    """User can be assigned to a case as judge."""


# ════════════════════════════════════════════════════════════════════
#  EVIDENCE APP — Standard CRUD + Custom Workflow
# ════════════════════════════════════════════════════════════════════

class EvidencePerms:
    """Standard + custom permissions for the evidence app."""

    # ── Evidence (base) — standard CRUD ─────────────────────────────
    VIEW_EVIDENCE = "view_evidence"
    ADD_EVIDENCE = "add_evidence"
    CHANGE_EVIDENCE = "change_evidence"
    DELETE_EVIDENCE = "delete_evidence"

    # ── TestimonyEvidence — standard CRUD ───────────────────────────
    VIEW_TESTIMONYEVIDENCE = "view_testimonyevidence"
    ADD_TESTIMONYEVIDENCE = "add_testimonyevidence"
    CHANGE_TESTIMONYEVIDENCE = "change_testimonyevidence"
    DELETE_TESTIMONYEVIDENCE = "delete_testimonyevidence"

    # ── BiologicalEvidence — standard CRUD ──────────────────────────
    VIEW_BIOLOGICALEVIDENCE = "view_biologicalevidence"
    ADD_BIOLOGICALEVIDENCE = "add_biologicalevidence"
    CHANGE_BIOLOGICALEVIDENCE = "change_biologicalevidence"
    DELETE_BIOLOGICALEVIDENCE = "delete_biologicalevidence"

    # ── VehicleEvidence — standard CRUD ─────────────────────────────
    VIEW_VEHICLEEVIDENCE = "view_vehicleevidence"
    ADD_VEHICLEEVIDENCE = "add_vehicleevidence"
    CHANGE_VEHICLEEVIDENCE = "change_vehicleevidence"
    DELETE_VEHICLEEVIDENCE = "delete_vehicleevidence"

    # ── IdentityEvidence — standard CRUD ────────────────────────────
    VIEW_IDENTITYEVIDENCE = "view_identityevidence"
    ADD_IDENTITYEVIDENCE = "add_identityevidence"
    CHANGE_IDENTITYEVIDENCE = "change_identityevidence"
    DELETE_IDENTITYEVIDENCE = "delete_identityevidence"

    # ── EvidenceFile — standard CRUD ────────────────────────────────
    VIEW_EVIDENCEFILE = "view_evidencefile"
    ADD_EVIDENCEFILE = "add_evidencefile"
    CHANGE_EVIDENCEFILE = "change_evidencefile"
    DELETE_EVIDENCEFILE = "delete_evidencefile"

    # ── Custom workflow permissions ─────────────────────────────────
    CAN_VERIFY_EVIDENCE = "can_verify_evidence"
    """Coroner examines and verifies biological / medical evidence."""

    CAN_REGISTER_FORENSIC_RESULT = "can_register_forensic_result"
    """Coroner fills in the forensic result for biological evidence."""


# ════════════════════════════════════════════════════════════════════
#  SUSPECTS APP — Standard CRUD + Custom Workflow
# ════════════════════════════════════════════════════════════════════

class SuspectsPerms:
    """Standard + custom permissions for the suspects app."""

    # ── Suspect — standard CRUD ─────────────────────────────────────
    VIEW_SUSPECT = "view_suspect"
    ADD_SUSPECT = "add_suspect"
    CHANGE_SUSPECT = "change_suspect"
    DELETE_SUSPECT = "delete_suspect"

    # ── Interrogation — standard CRUD ───────────────────────────────
    VIEW_INTERROGATION = "view_interrogation"
    ADD_INTERROGATION = "add_interrogation"
    CHANGE_INTERROGATION = "change_interrogation"
    DELETE_INTERROGATION = "delete_interrogation"

    # ── Trial — standard CRUD ──────────────────────────────────────
    VIEW_TRIAL = "view_trial"
    ADD_TRIAL = "add_trial"
    CHANGE_TRIAL = "change_trial"
    DELETE_TRIAL = "delete_trial"

    # ── BountyTip — standard CRUD ──────────────────────────────────
    VIEW_BOUNTYTIP = "view_bountytip"
    ADD_BOUNTYTIP = "add_bountytip"
    CHANGE_BOUNTYTIP = "change_bountytip"
    DELETE_BOUNTYTIP = "delete_bountytip"

    # ── Bail — standard CRUD ───────────────────────────────────────
    VIEW_BAIL = "view_bail"
    ADD_BAIL = "add_bail"
    CHANGE_BAIL = "change_bail"
    DELETE_BAIL = "delete_bail"

    # ── Custom workflow permissions ─────────────────────────────────
    CAN_IDENTIFY_SUSPECT = "can_identify_suspect"
    """Detective identifies and declares suspects for a case."""

    CAN_APPROVE_SUSPECT = "can_approve_suspect"
    """Sergeant approves or rejects identified suspects."""

    CAN_ISSUE_ARREST_WARRANT = "can_issue_arrest_warrant"
    """Sergeant issues an arrest warrant for an approved suspect."""

    CAN_CONDUCT_INTERROGATION = "can_conduct_interrogation"
    """Sergeant and Detective conduct the interrogation session."""

    CAN_SCORE_GUILT = "can_score_guilt"
    """Sergeant / Detective assigns a guilt probability score (1–10)."""

    CAN_RENDER_VERDICT = "can_render_verdict"
    """Captain gives the final guilty/innocent verdict (or Police Chief for critical)."""

    CAN_JUDGE_TRIAL = "can_judge_trial"
    """Judge presides over the trial, records verdict and punishment."""

    CAN_REVIEW_BOUNTY_TIP = "can_review_bounty_tip"
    """Police Officer does the initial review of bounty tips."""

    CAN_VERIFY_BOUNTY_TIP = "can_verify_bounty_tip"
    """Detective verifies bounty tip information."""

    CAN_SET_BAIL_AMOUNT = "can_set_bail_amount"
    """Sergeant determines the bail / fine amount."""

    # ── Scope permissions (data-visibility tiers) ───────────────────
    CAN_SCOPE_ALL_SUSPECTS = "can_scope_all_suspects"
    """Unrestricted suspect/interrogation/trial/bail visibility."""

    CAN_SCOPE_ASSIGNED_SUSPECTS = "can_scope_assigned_suspects"
    """Detective: suspects on assigned cases or identified by this user."""

    CAN_SCOPE_SUPERVISED_SUSPECTS = "can_scope_supervised_suspects"
    """Sergeant: suspects on supervised cases or pending approval."""

    CAN_SCOPE_EXAMINED_SUSPECTS = "can_scope_examined_suspects"
    """Coroner: suspects on cases where this user registered evidence."""

    CAN_SCOPE_OWN_SUSPECTS = "can_scope_own_suspects"
    """Base User: suspects on cases the user is associated with."""

    # ── Workflow guard permissions ──────────────────────────────────
    CAN_LOOKUP_BOUNTY_REWARD = "can_lookup_bounty_reward"
    """Police ranks can look up bounty reward info."""


# ════════════════════════════════════════════════════════════════════
#  BOARD APP — Standard CRUD + Custom Workflow
# ════════════════════════════════════════════════════════════════════

class BoardPerms:
    """Standard + custom permissions for the board (detective board) app."""

    # ── DetectiveBoard — standard CRUD ──────────────────────────────
    VIEW_DETECTIVEBOARD = "view_detectiveboard"
    ADD_DETECTIVEBOARD = "add_detectiveboard"
    CHANGE_DETECTIVEBOARD = "change_detectiveboard"
    DELETE_DETECTIVEBOARD = "delete_detectiveboard"

    # ── BoardNote — standard CRUD ──────────────────────────────────
    VIEW_BOARDNOTE = "view_boardnote"
    ADD_BOARDNOTE = "add_boardnote"
    CHANGE_BOARDNOTE = "change_boardnote"
    DELETE_BOARDNOTE = "delete_boardnote"

    # ── BoardItem — standard CRUD ──────────────────────────────────
    VIEW_BOARDITEM = "view_boarditem"
    ADD_BOARDITEM = "add_boarditem"
    CHANGE_BOARDITEM = "change_boarditem"
    DELETE_BOARDITEM = "delete_boarditem"

    # ── BoardConnection — standard CRUD ────────────────────────────
    VIEW_BOARDCONNECTION = "view_boardconnection"
    ADD_BOARDCONNECTION = "add_boardconnection"
    CHANGE_BOARDCONNECTION = "change_boardconnection"
    DELETE_BOARDCONNECTION = "delete_boardconnection"

    # ── Custom workflow permissions ─────────────────────────────────
    CAN_EXPORT_BOARD = "can_export_board"
    """Detective exports the board as an image for reports."""

    CAN_CREATE_BOARD = "can_create_board"
    """Can create a new detective board (Detective, Supervisors, Admin)."""

    CAN_VIEW_ANY_BOARD = "can_view_any_board"
    """Supervisor-level: can view boards on cases assigned to them."""


# ════════════════════════════════════════════════════════════════════
#  CORE APP — Standard CRUD
# ════════════════════════════════════════════════════════════════════

class CorePerms:
    """Standard CRUD permissions for core models."""

    # ── Notification — standard CRUD ────────────────────────────────
    VIEW_NOTIFICATION = "view_notification"
    ADD_NOTIFICATION = "add_notification"
    CHANGE_NOTIFICATION = "change_notification"
    DELETE_NOTIFICATION = "delete_notification"

    # ── Custom workflow permissions ─────────────────────────────────
    CAN_VIEW_FULL_DASHBOARD = "can_view_full_dashboard"
    """Full department-wide dashboard statistics access."""

    CAN_SEARCH_ALL = "can_search_all"
    """Unrestricted global search across all cases/suspects/evidence."""
