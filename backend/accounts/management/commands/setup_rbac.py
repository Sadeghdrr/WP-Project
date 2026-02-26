"""
Management command: setup_rbac
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Seeds the database with base **Roles** and links each role to its
set of Django permissions.

Key design principle — **this command does NOT create Permission objects**.
Permissions must already exist in the database:
    • Standard CRUD permissions are auto-created by Django after
      ``migrate`` (one per model × {add, change, delete, view}).
    • Custom workflow permissions are declared in each model's
      ``Meta.permissions`` tuple and inserted by ``migrate``.

The command is **idempotent** — safe to run multiple times.  Existing
roles are updated; permissions are replaced (set) to match the
mapping below.

Usage::

    python manage.py setup_rbac

Prerequisites::

    python manage.py makemigrations
    python manage.py migrate
"""

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from accounts.models import Role
from core.permissions_constants import (
    AccountsPerms,
    BoardPerms,
    CasesPerms,
    CorePerms,
    EvidencePerms,
    SuspectsPerms,
)

# ────────────────────────────────────────────────────────────────────
# Role → Permission mapping  (uses constants — zero hard-coded strings)
# ────────────────────────────────────────────────────────────────────
# Key:   (role_name, description, hierarchy_level)
# Value: list of codenames from ``core.permissions_constants``

ROLE_PERMISSIONS_MAP: dict[tuple[str, str, int], list[str]] = {

    # ── System Administrator ────────────────────────────────────────
    (
        "System Admin",
        "Full system access — manages users, roles, and all data.",
        100,
    ): [
        # Accounts
        AccountsPerms.VIEW_ROLE, AccountsPerms.ADD_ROLE,
        AccountsPerms.CHANGE_ROLE, AccountsPerms.DELETE_ROLE,
        AccountsPerms.VIEW_USER, AccountsPerms.ADD_USER,
        AccountsPerms.CHANGE_USER, AccountsPerms.DELETE_USER,
        # Cases (standard + custom)
        CasesPerms.VIEW_CASE, CasesPerms.ADD_CASE,
        CasesPerms.CHANGE_CASE, CasesPerms.DELETE_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT, CasesPerms.ADD_CASECOMPLAINANT,
        CasesPerms.CHANGE_CASECOMPLAINANT, CasesPerms.DELETE_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS, CasesPerms.ADD_CASEWITNESS,
        CasesPerms.CHANGE_CASEWITNESS, CasesPerms.DELETE_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG, CasesPerms.ADD_CASESTATUSLOG,
        CasesPerms.CHANGE_CASESTATUSLOG, CasesPerms.DELETE_CASESTATUSLOG,
        CasesPerms.CAN_REVIEW_COMPLAINT, CasesPerms.CAN_APPROVE_CASE,
        CasesPerms.CAN_ASSIGN_DETECTIVE, CasesPerms.CAN_CHANGE_CASE_STATUS,
        CasesPerms.CAN_FORWARD_TO_JUDICIARY, CasesPerms.CAN_APPROVE_CRITICAL_CASE,
        # Evidence (standard + custom)
        EvidencePerms.VIEW_EVIDENCE, EvidencePerms.ADD_EVIDENCE,
        EvidencePerms.CHANGE_EVIDENCE, EvidencePerms.DELETE_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE, EvidencePerms.ADD_TESTIMONYEVIDENCE,
        EvidencePerms.CHANGE_TESTIMONYEVIDENCE, EvidencePerms.DELETE_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE, EvidencePerms.ADD_BIOLOGICALEVIDENCE,
        EvidencePerms.CHANGE_BIOLOGICALEVIDENCE, EvidencePerms.DELETE_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE, EvidencePerms.ADD_VEHICLEEVIDENCE,
        EvidencePerms.CHANGE_VEHICLEEVIDENCE, EvidencePerms.DELETE_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE, EvidencePerms.ADD_IDENTITYEVIDENCE,
        EvidencePerms.CHANGE_IDENTITYEVIDENCE, EvidencePerms.DELETE_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE, EvidencePerms.ADD_EVIDENCEFILE,
        EvidencePerms.CHANGE_EVIDENCEFILE, EvidencePerms.DELETE_EVIDENCEFILE,
        EvidencePerms.CAN_VERIFY_EVIDENCE, EvidencePerms.CAN_REGISTER_FORENSIC_RESULT,
        # Suspects (standard + custom)
        SuspectsPerms.VIEW_SUSPECT, SuspectsPerms.ADD_SUSPECT,
        SuspectsPerms.CHANGE_SUSPECT, SuspectsPerms.DELETE_SUSPECT,
        SuspectsPerms.VIEW_INTERROGATION, SuspectsPerms.ADD_INTERROGATION,
        SuspectsPerms.CHANGE_INTERROGATION, SuspectsPerms.DELETE_INTERROGATION,
        SuspectsPerms.VIEW_TRIAL, SuspectsPerms.ADD_TRIAL,
        SuspectsPerms.CHANGE_TRIAL, SuspectsPerms.DELETE_TRIAL,
        SuspectsPerms.VIEW_BOUNTYTIP, SuspectsPerms.ADD_BOUNTYTIP,
        SuspectsPerms.CHANGE_BOUNTYTIP, SuspectsPerms.DELETE_BOUNTYTIP,
        SuspectsPerms.VIEW_BAIL, SuspectsPerms.ADD_BAIL,
        SuspectsPerms.CHANGE_BAIL, SuspectsPerms.DELETE_BAIL,
        SuspectsPerms.CAN_IDENTIFY_SUSPECT, SuspectsPerms.CAN_APPROVE_SUSPECT,
        SuspectsPerms.CAN_ISSUE_ARREST_WARRANT, SuspectsPerms.CAN_CONDUCT_INTERROGATION,
        SuspectsPerms.CAN_SCORE_GUILT, SuspectsPerms.CAN_RENDER_VERDICT,
        SuspectsPerms.CAN_JUDGE_TRIAL, SuspectsPerms.CAN_REVIEW_BOUNTY_TIP,
        SuspectsPerms.CAN_VERIFY_BOUNTY_TIP, SuspectsPerms.CAN_SET_BAIL_AMOUNT,
        # Board
        BoardPerms.VIEW_DETECTIVEBOARD, BoardPerms.ADD_DETECTIVEBOARD,
        BoardPerms.CHANGE_DETECTIVEBOARD, BoardPerms.DELETE_DETECTIVEBOARD,
        BoardPerms.VIEW_BOARDNOTE, BoardPerms.ADD_BOARDNOTE,
        BoardPerms.CHANGE_BOARDNOTE, BoardPerms.DELETE_BOARDNOTE,
        BoardPerms.VIEW_BOARDITEM, BoardPerms.ADD_BOARDITEM,
        BoardPerms.CHANGE_BOARDITEM, BoardPerms.DELETE_BOARDITEM,
        BoardPerms.VIEW_BOARDCONNECTION, BoardPerms.ADD_BOARDCONNECTION,
        BoardPerms.CHANGE_BOARDCONNECTION, BoardPerms.DELETE_BOARDCONNECTION,
        BoardPerms.CAN_EXPORT_BOARD,
        # Core
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Police Chief ────────────────────────────────────────────────
    (
        "Police Chief",
        "Highest police rank — approves critical-level cases and forwards to judiciary.",
        10,
    ): [
        # Cases
        CasesPerms.VIEW_CASE, CasesPerms.ADD_CASE, CasesPerms.CHANGE_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT, CasesPerms.CHANGE_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS, CasesPerms.ADD_CASEWITNESS, CasesPerms.CHANGE_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG, CasesPerms.ADD_CASESTATUSLOG,
        CasesPerms.CAN_APPROVE_CASE, CasesPerms.CAN_ASSIGN_DETECTIVE,
        CasesPerms.CAN_CHANGE_CASE_STATUS, CasesPerms.CAN_FORWARD_TO_JUDICIARY,
        CasesPerms.CAN_APPROVE_CRITICAL_CASE,
        # Evidence
        EvidencePerms.VIEW_EVIDENCE, EvidencePerms.ADD_EVIDENCE, EvidencePerms.CHANGE_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE, EvidencePerms.ADD_TESTIMONYEVIDENCE,
        EvidencePerms.CHANGE_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE, EvidencePerms.ADD_VEHICLEEVIDENCE,
        EvidencePerms.CHANGE_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE, EvidencePerms.ADD_IDENTITYEVIDENCE,
        EvidencePerms.CHANGE_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE, EvidencePerms.ADD_EVIDENCEFILE,
        # Suspects
        SuspectsPerms.VIEW_SUSPECT, SuspectsPerms.ADD_SUSPECT, SuspectsPerms.CHANGE_SUSPECT,
        SuspectsPerms.VIEW_INTERROGATION,
        SuspectsPerms.VIEW_TRIAL,
        SuspectsPerms.VIEW_BOUNTYTIP,
        SuspectsPerms.VIEW_BAIL, SuspectsPerms.CHANGE_BAIL,
        SuspectsPerms.CAN_RENDER_VERDICT,
        # Board (read-only)
        BoardPerms.VIEW_DETECTIVEBOARD,
        BoardPerms.VIEW_BOARDNOTE,
        BoardPerms.VIEW_BOARDITEM,
        BoardPerms.VIEW_BOARDCONNECTION,
        # Users (view only)
        AccountsPerms.VIEW_USER,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Captain ─────────────────────────────────────────────────────
    (
        "Captain",
        "Approves cases and forwards them to the judiciary for trial.",
        9,
    ): [
        # Cases
        CasesPerms.VIEW_CASE, CasesPerms.ADD_CASE, CasesPerms.CHANGE_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT, CasesPerms.CHANGE_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG, CasesPerms.ADD_CASESTATUSLOG,
        CasesPerms.CAN_APPROVE_CASE, CasesPerms.CAN_CHANGE_CASE_STATUS,
        CasesPerms.CAN_FORWARD_TO_JUDICIARY,
        # Evidence (read-only)
        EvidencePerms.VIEW_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE,
        # Suspects
        SuspectsPerms.VIEW_SUSPECT, SuspectsPerms.CHANGE_SUSPECT,
        SuspectsPerms.VIEW_INTERROGATION,
        SuspectsPerms.VIEW_TRIAL,
        SuspectsPerms.VIEW_BOUNTYTIP,
        SuspectsPerms.VIEW_BAIL,
        SuspectsPerms.CAN_RENDER_VERDICT,
        # Board (read-only)
        BoardPerms.VIEW_DETECTIVEBOARD,
        BoardPerms.VIEW_BOARDNOTE,
        BoardPerms.VIEW_BOARDITEM,
        BoardPerms.VIEW_BOARDCONNECTION,
        # Users
        AccountsPerms.VIEW_USER,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Sergeant ────────────────────────────────────────────────────
    (
        "Sergeant",
        "Supervises detectives, issues arrest warrants, conducts interrogations.",
        8,
    ): [
        # Cases
        CasesPerms.VIEW_CASE, CasesPerms.CHANGE_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG, CasesPerms.ADD_CASESTATUSLOG,
        CasesPerms.CAN_CHANGE_CASE_STATUS,
        # Evidence (read-only)
        EvidencePerms.VIEW_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE,
        # Suspects (approve, interrogate, bail)
        SuspectsPerms.VIEW_SUSPECT, SuspectsPerms.CHANGE_SUSPECT,
        SuspectsPerms.VIEW_INTERROGATION, SuspectsPerms.ADD_INTERROGATION,
        SuspectsPerms.CHANGE_INTERROGATION,
        SuspectsPerms.VIEW_TRIAL,
        SuspectsPerms.VIEW_BOUNTYTIP,
        SuspectsPerms.VIEW_BAIL, SuspectsPerms.ADD_BAIL, SuspectsPerms.CHANGE_BAIL,
        SuspectsPerms.CAN_APPROVE_SUSPECT, SuspectsPerms.CAN_ISSUE_ARREST_WARRANT,
        SuspectsPerms.CAN_CONDUCT_INTERROGATION, SuspectsPerms.CAN_SCORE_GUILT,
        SuspectsPerms.CAN_SET_BAIL_AMOUNT,
        # Board (read-only)
        BoardPerms.VIEW_DETECTIVEBOARD,
        BoardPerms.VIEW_BOARDNOTE,
        BoardPerms.VIEW_BOARDITEM,
        BoardPerms.VIEW_BOARDCONNECTION,
        # Users
        AccountsPerms.VIEW_USER,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Detective ───────────────────────────────────────────────────
    (
        "Detective",
        "Investigates cases, manages detective board, identifies suspects.",
        7,
    ): [
        # Cases
        CasesPerms.VIEW_CASE, CasesPerms.CHANGE_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS, CasesPerms.ADD_CASEWITNESS, CasesPerms.CHANGE_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG, CasesPerms.ADD_CASESTATUSLOG,
        CasesPerms.CAN_CHANGE_CASE_STATUS,
        # Evidence (full create/edit)
        EvidencePerms.VIEW_EVIDENCE, EvidencePerms.ADD_EVIDENCE, EvidencePerms.CHANGE_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE, EvidencePerms.ADD_TESTIMONYEVIDENCE,
        EvidencePerms.CHANGE_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE, EvidencePerms.ADD_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE, EvidencePerms.ADD_VEHICLEEVIDENCE,
        EvidencePerms.CHANGE_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE, EvidencePerms.ADD_IDENTITYEVIDENCE,
        EvidencePerms.CHANGE_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE, EvidencePerms.ADD_EVIDENCEFILE,
        EvidencePerms.CHANGE_EVIDENCEFILE,
        # Suspects (identify + interrogate)
        SuspectsPerms.VIEW_SUSPECT, SuspectsPerms.ADD_SUSPECT, SuspectsPerms.CHANGE_SUSPECT,
        SuspectsPerms.VIEW_INTERROGATION, SuspectsPerms.ADD_INTERROGATION,
        SuspectsPerms.CHANGE_INTERROGATION,
        SuspectsPerms.VIEW_TRIAL,
        SuspectsPerms.VIEW_BOUNTYTIP, SuspectsPerms.CHANGE_BOUNTYTIP,
        SuspectsPerms.VIEW_BAIL,
        SuspectsPerms.CAN_IDENTIFY_SUSPECT, SuspectsPerms.CAN_CONDUCT_INTERROGATION,
        SuspectsPerms.CAN_SCORE_GUILT, SuspectsPerms.CAN_VERIFY_BOUNTY_TIP,
        # Board (full CRUD — detective's workspace)
        BoardPerms.VIEW_DETECTIVEBOARD, BoardPerms.ADD_DETECTIVEBOARD,
        BoardPerms.CHANGE_DETECTIVEBOARD, BoardPerms.DELETE_DETECTIVEBOARD,
        BoardPerms.VIEW_BOARDNOTE, BoardPerms.ADD_BOARDNOTE,
        BoardPerms.CHANGE_BOARDNOTE, BoardPerms.DELETE_BOARDNOTE,
        BoardPerms.VIEW_BOARDITEM, BoardPerms.ADD_BOARDITEM,
        BoardPerms.CHANGE_BOARDITEM, BoardPerms.DELETE_BOARDITEM,
        BoardPerms.VIEW_BOARDCONNECTION, BoardPerms.ADD_BOARDCONNECTION,
        BoardPerms.CHANGE_BOARDCONNECTION, BoardPerms.DELETE_BOARDCONNECTION,
        BoardPerms.CAN_EXPORT_BOARD,
        # Users
        AccountsPerms.VIEW_USER,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Police Officer ──────────────────────────────────────────────
    (
        "Police Officer",
        "Field officer — creates crime-scene cases, reviews cadet submissions.",
        6,
    ): [
        # Cases
        CasesPerms.VIEW_CASE, CasesPerms.ADD_CASE, CasesPerms.CHANGE_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS, CasesPerms.ADD_CASEWITNESS, CasesPerms.CHANGE_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG, CasesPerms.ADD_CASESTATUSLOG,
        CasesPerms.CAN_APPROVE_CASE, CasesPerms.CAN_CHANGE_CASE_STATUS,
        # Evidence (register)
        EvidencePerms.VIEW_EVIDENCE, EvidencePerms.ADD_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE, EvidencePerms.ADD_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE, EvidencePerms.ADD_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE, EvidencePerms.ADD_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE, EvidencePerms.ADD_EVIDENCEFILE,
        # Suspects
        SuspectsPerms.VIEW_SUSPECT,
        SuspectsPerms.VIEW_BOUNTYTIP, SuspectsPerms.CHANGE_BOUNTYTIP,
        SuspectsPerms.CAN_REVIEW_BOUNTY_TIP,
        # Users
        AccountsPerms.VIEW_USER,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Cadet ───────────────────────────────────────────────────────
    (
        "Cadet",
        "Lowest police rank — reviews and filters incoming complaints.",
        4,
    ): [
        # Cases
        CasesPerms.VIEW_CASE, CasesPerms.CHANGE_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT, CasesPerms.CHANGE_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG, CasesPerms.ADD_CASESTATUSLOG,
        CasesPerms.CAN_REVIEW_COMPLAINT, CasesPerms.CAN_CHANGE_CASE_STATUS,
        # Evidence (view only)
        EvidencePerms.VIEW_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE,
        # Users
        AccountsPerms.VIEW_USER,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Coroner ─────────────────────────────────────────────────────
    (
        "Coroner",
        "Examines and verifies biological/medical evidence.",
        3,
    ): [
        # Cases (read-only)
        CasesPerms.VIEW_CASE,
        # Evidence (view all + verify biological)
        EvidencePerms.VIEW_EVIDENCE, EvidencePerms.CHANGE_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE, EvidencePerms.CHANGE_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE, EvidencePerms.ADD_EVIDENCEFILE,
        EvidencePerms.CAN_VERIFY_EVIDENCE, EvidencePerms.CAN_REGISTER_FORENSIC_RESULT,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Judge ───────────────────────────────────────────────────────
    (
        "Judge",
        "Presides over trials — access to full case files, evidence, and personnel.",
        2,
    ): [
        # Cases (read-only, full access to review)
        CasesPerms.VIEW_CASE,
        CasesPerms.VIEW_CASECOMPLAINANT,
        CasesPerms.VIEW_CASEWITNESS,
        CasesPerms.VIEW_CASESTATUSLOG,
        # Evidence (read-only)
        EvidencePerms.VIEW_EVIDENCE,
        EvidencePerms.VIEW_TESTIMONYEVIDENCE,
        EvidencePerms.VIEW_BIOLOGICALEVIDENCE,
        EvidencePerms.VIEW_VEHICLEEVIDENCE,
        EvidencePerms.VIEW_IDENTITYEVIDENCE,
        EvidencePerms.VIEW_EVIDENCEFILE,
        # Suspects & trials
        SuspectsPerms.VIEW_SUSPECT,
        SuspectsPerms.VIEW_INTERROGATION,
        SuspectsPerms.VIEW_TRIAL, SuspectsPerms.ADD_TRIAL, SuspectsPerms.CHANGE_TRIAL,
        SuspectsPerms.VIEW_BAIL,
        SuspectsPerms.CAN_JUDGE_TRIAL,
        # Users
        AccountsPerms.VIEW_USER,
        # Notifications
        CorePerms.VIEW_NOTIFICATION, CorePerms.ADD_NOTIFICATION,
        CorePerms.CHANGE_NOTIFICATION, CorePerms.DELETE_NOTIFICATION,
    ],

    # ── Base User ───────────────────────────────────────────────────
    (
        "Base User",
        "Default role for newly registered users before assignment.",
        0,
    ): [
        SuspectsPerms.VIEW_SUSPECT,       # Most Wanted page is public
        SuspectsPerms.VIEW_BOUNTYTIP, SuspectsPerms.ADD_BOUNTYTIP,
        CorePerms.VIEW_NOTIFICATION, CorePerms.CHANGE_NOTIFICATION,
    ],
}


class Command(BaseCommand):
    help = (
        "Seeds the database with base Roles and maps each role to its "
        "Django permissions.  Safe to run multiple times (idempotent).  "
        "Does NOT create permissions — run `migrate` first."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n══════════════════════════════════════════"
            "\n  RBAC Setup — Seeding Roles & Permissions"
            "\n══════════════════════════════════════════\n"
        ))

        # Pre-fetch ALL permissions into a dict for fast look-up
        all_permissions: dict[str, Permission] = {
            p.codename: p
            for p in Permission.objects.select_related("content_type").all()
        }

        roles_created = 0
        roles_updated = 0
        warnings = 0

        for (role_name, description, hierarchy_level), codenames in ROLE_PERMISSIONS_MAP.items():
            # ── 1. Idempotent role creation / update ────────────────
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    "description": description,
                    "hierarchy_level": hierarchy_level,
                },
            )

            if not created:
                changed = False
                if role.description != description:
                    role.description = description
                    changed = True
                if role.hierarchy_level != hierarchy_level:
                    role.hierarchy_level = hierarchy_level
                    changed = True
                if changed:
                    role.save(update_fields=["description", "hierarchy_level"])

            # ── 2. Resolve permission codenames ─────────────────────
            resolved_permissions: list[Permission] = []
            for codename in codenames:
                perm = all_permissions.get(codename)
                if perm is not None:
                    resolved_permissions.append(perm)
                else:
                    warnings += 1
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠  Permission '{codename}' not found — "
                        f"skipped for role '{role_name}'.  "
                        f"(Run makemigrations & migrate first?)"
                    ))

            # ── 3. Set permissions (replaces old set entirely) ──────
            role.permissions.set(resolved_permissions)

            # ── 4. Console output ───────────────────────────────────
            action = "Created" if created else "Updated"
            if created:
                roles_created += 1
            else:
                roles_updated += 1

            self.stdout.write(self.style.SUCCESS(
                f"  ✔  {action} role: {role_name:<20s} "
                f"(hierarchy={hierarchy_level}, "
                f"permissions={len(resolved_permissions)})"
            ))

        # ── Summary ─────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n──────────────────────────────────────────"
        ))
        summary = (
            f"  Done!  {roles_created} role(s) created, "
            f"{roles_updated} role(s) updated.  "
            f"Total: {roles_created + roles_updated} role(s)."
        )
        if warnings:
            summary += f"  ({warnings} permission warning(s) — see above.)"
        self.stdout.write(self.style.SUCCESS(summary + "\n"))
