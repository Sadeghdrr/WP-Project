"""
Management command: setup_rbac
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Populates the database with the base Roles and their initial
Permission mappings for the L.A. Noire police-department system.

This command is **idempotent** — it can be run multiple times without
creating duplicates or crashing.  Existing roles are updated to match
the mapping defined here; permissions that no longer appear are removed
from the role.

Usage::

    python manage.py setup_rbac
"""

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

from accounts.models import Role


# ────────────────────────────────────────────────────────────────────
# Role → Permission mapping
# ────────────────────────────────────────────────────────────────────
# Each key is a tuple:  (role_name, description, hierarchy_level)
# Each value is a list of Django permission codenames.
#
# Standard codename format:  <action>_<model>
#   e.g.  view_case, add_evidence, change_suspect, delete_user
#
# To add new permissions later:
#   1. Add the codename to the appropriate role's list below.
#   2. Make sure the permission exists (either via model Meta.permissions
#      or Django's auto-generated CRUD permissions after migrations).
#   3. Re-run:  python manage.py setup_rbac
# ────────────────────────────────────────────────────────────────────

ROLE_PERMISSIONS_MAP: dict[tuple[str, str, int], list[str]] = {

    # ── System Administrator ────────────────────────────────────────
    ("System Admin", "Full system access — manages users, roles, and all data.", 100): [
        # Accounts
        "view_role", "add_role", "change_role", "delete_role",
        "view_user", "add_user", "change_user", "delete_user",
        # Cases
        "view_case", "add_case", "change_case", "delete_case",
        "view_casecomplainant", "add_casecomplainant", "change_casecomplainant", "delete_casecomplainant",
        "view_casewitness", "add_casewitness", "change_casewitness", "delete_casewitness",
        "view_casestatuslog", "add_casestatuslog", "change_casestatuslog", "delete_casestatuslog",
        # Evidence
        "view_evidence", "add_evidence", "change_evidence", "delete_evidence",
        "view_testimonyevidence", "add_testimonyevidence", "change_testimonyevidence", "delete_testimonyevidence",
        "view_biologicalevidence", "add_biologicalevidence", "change_biologicalevidence", "delete_biologicalevidence",
        "view_vehicleevidence", "add_vehicleevidence", "change_vehicleevidence", "delete_vehicleevidence",
        "view_identityevidence", "add_identityevidence", "change_identityevidence", "delete_identityevidence",
        "view_evidencefile", "add_evidencefile", "change_evidencefile", "delete_evidencefile",
        # Suspects
        "view_suspect", "add_suspect", "change_suspect", "delete_suspect",
        "view_interrogation", "add_interrogation", "change_interrogation", "delete_interrogation",
        "view_trial", "add_trial", "change_trial", "delete_trial",
        "view_bountytip", "add_bountytip", "change_bountytip", "delete_bountytip",
        "view_bail", "add_bail", "change_bail", "delete_bail",
        # Board
        "view_detectiveboard", "add_detectiveboard", "change_detectiveboard", "delete_detectiveboard",
        "view_boardnote", "add_boardnote", "change_boardnote", "delete_boardnote",
        "view_boarditem", "add_boarditem", "change_boarditem", "delete_boarditem",
        "view_boardconnection", "add_boardconnection", "change_boardconnection", "delete_boardconnection",
        # Core
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Police Chief ────────────────────────────────────────────────
    ("Police Chief", "Highest police rank — approves critical-level cases and forwards to judiciary.", 10): [
        # Cases (full view/create/change, no delete)
        "view_case", "add_case", "change_case",
        "view_casecomplainant", "change_casecomplainant",
        "view_casewitness", "add_casewitness", "change_casewitness",
        "view_casestatuslog", "add_casestatuslog",
        # Evidence (read + register)
        "view_evidence", "add_evidence", "change_evidence",
        "view_testimonyevidence", "add_testimonyevidence", "change_testimonyevidence",
        "view_biologicalevidence",
        "view_vehicleevidence", "add_vehicleevidence", "change_vehicleevidence",
        "view_identityevidence", "add_identityevidence", "change_identityevidence",
        "view_evidencefile", "add_evidencefile",
        # Suspects
        "view_suspect", "add_suspect", "change_suspect",
        "view_interrogation",
        "view_trial",
        "view_bountytip",
        "view_bail", "change_bail",
        # Board (read-only)
        "view_detectiveboard",
        "view_boardnote",
        "view_boarditem",
        "view_boardconnection",
        # Users (view only)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Captain ─────────────────────────────────────────────────────
    ("Captain", "Approves cases and forwards them to the judiciary for trial.", 9): [
        # Cases
        "view_case", "add_case", "change_case",
        "view_casecomplainant", "change_casecomplainant",
        "view_casewitness",
        "view_casestatuslog", "add_casestatuslog",
        # Evidence (read-only)
        "view_evidence",
        "view_testimonyevidence",
        "view_biologicalevidence",
        "view_vehicleevidence",
        "view_identityevidence",
        "view_evidencefile",
        # Suspects
        "view_suspect", "change_suspect",
        "view_interrogation",
        "view_trial",
        "view_bountytip",
        "view_bail",
        # Board (read-only)
        "view_detectiveboard",
        "view_boardnote",
        "view_boarditem",
        "view_boardconnection",
        # Users (view only)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Sergeant ────────────────────────────────────────────────────
    ("Sergeant", "Supervises detectives, issues arrest warrants, conducts interrogations.", 8): [
        # Cases
        "view_case", "change_case",
        "view_casecomplainant",
        "view_casewitness",
        "view_casestatuslog", "add_casestatuslog",
        # Evidence (read-only)
        "view_evidence",
        "view_testimonyevidence",
        "view_biologicalevidence",
        "view_vehicleevidence",
        "view_identityevidence",
        "view_evidencefile",
        # Suspects (approve suspects, interrogate)
        "view_suspect", "change_suspect",
        "view_interrogation", "add_interrogation", "change_interrogation",
        "view_trial",
        "view_bountytip",
        "view_bail", "add_bail", "change_bail",
        # Board (read-only)
        "view_detectiveboard",
        "view_boardnote",
        "view_boarditem",
        "view_boardconnection",
        # Users (view only)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Detective ───────────────────────────────────────────────────
    ("Detective", "Investigates cases, manages detective board, identifies suspects.", 7): [
        # Cases
        "view_case", "change_case",
        "view_casecomplainant",
        "view_casewitness", "add_casewitness", "change_casewitness",
        "view_casestatuslog", "add_casestatuslog",
        # Evidence (full create/edit)
        "view_evidence", "add_evidence", "change_evidence",
        "view_testimonyevidence", "add_testimonyevidence", "change_testimonyevidence",
        "view_biologicalevidence", "add_biologicalevidence",
        "view_vehicleevidence", "add_vehicleevidence", "change_vehicleevidence",
        "view_identityevidence", "add_identityevidence", "change_identityevidence",
        "view_evidencefile", "add_evidencefile", "change_evidencefile",
        # Suspects (identify + interrogate)
        "view_suspect", "add_suspect", "change_suspect",
        "view_interrogation", "add_interrogation", "change_interrogation",
        "view_trial",
        "view_bountytip", "change_bountytip",       # verify tips
        "view_bail",
        # Board (full CRUD — detective's workspace)
        "view_detectiveboard", "add_detectiveboard", "change_detectiveboard", "delete_detectiveboard",
        "view_boardnote", "add_boardnote", "change_boardnote", "delete_boardnote",
        "view_boarditem", "add_boarditem", "change_boarditem", "delete_boarditem",
        "view_boardconnection", "add_boardconnection", "change_boardconnection", "delete_boardconnection",
        # Users (view only)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Police Officer ──────────────────────────────────────────────
    ("Police Officer", "Field officer — creates crime-scene cases, reviews cadet submissions.", 6): [
        # Cases (create crime-scene + approve after cadet)
        "view_case", "add_case", "change_case",
        "view_casecomplainant",
        "view_casewitness", "add_casewitness", "change_casewitness",
        "view_casestatuslog", "add_casestatuslog",
        # Evidence (register)
        "view_evidence", "add_evidence",
        "view_testimonyevidence", "add_testimonyevidence",
        "view_biologicalevidence",
        "view_vehicleevidence", "add_vehicleevidence",
        "view_identityevidence", "add_identityevidence",
        "view_evidencefile", "add_evidencefile",
        # Suspects (view only)
        "view_suspect",
        "view_bountytip", "change_bountytip",       # review tips
        # Users (view only)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Patrol Officer ──────────────────────────────────────────────
    ("Patrol Officer", "Field patrol — reports crime scenes and suspicious activity.", 5): [
        # Cases
        "view_case", "add_case", "change_case",
        "view_casecomplainant",
        "view_casewitness", "add_casewitness", "change_casewitness",
        "view_casestatuslog", "add_casestatuslog",
        # Evidence (register)
        "view_evidence", "add_evidence",
        "view_testimonyevidence", "add_testimonyevidence",
        "view_vehicleevidence", "add_vehicleevidence",
        "view_identityevidence", "add_identityevidence",
        "view_evidencefile", "add_evidencefile",
        # Suspects (view only)
        "view_suspect",
        # Users (view only)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Cadet ───────────────────────────────────────────────────────
    ("Cadet", "Lowest police rank — reviews and filters incoming complaints.", 4): [
        # Cases (review complaints, change status)
        "view_case", "change_case",
        "view_casecomplainant", "change_casecomplainant",
        "view_casewitness",
        "view_casestatuslog", "add_casestatuslog",
        # Evidence (view only)
        "view_evidence",
        "view_testimonyevidence",
        "view_evidencefile",
        # Users (view only)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Coroner ─────────────────────────────────────────────────────
    ("Coroner", "Examines and verifies biological/medical evidence.", 3): [
        # Cases (read-only)
        "view_case",
        # Evidence (view all + change biological)
        "view_evidence", "change_evidence",
        "view_testimonyevidence",
        "view_biologicalevidence", "change_biologicalevidence",
        "view_vehicleevidence",
        "view_identityevidence",
        "view_evidencefile", "add_evidencefile",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Judge ───────────────────────────────────────────────────────
    ("Judge", "Presides over trials — access to full case files, evidence, and personnel.", 2): [
        # Cases (read-only, full access to review)
        "view_case",
        "view_casecomplainant",
        "view_casewitness",
        "view_casestatuslog",
        # Evidence (read-only)
        "view_evidence",
        "view_testimonyevidence",
        "view_biologicalevidence",
        "view_vehicleevidence",
        "view_identityevidence",
        "view_evidencefile",
        # Suspects & trials
        "view_suspect",
        "view_interrogation",
        "view_trial", "add_trial", "change_trial",
        "view_bail",
        # Users (view personnel involved)
        "view_user",
        # Notifications
        "view_notification", "add_notification", "change_notification", "delete_notification",
    ],

    # ── Complainant ─────────────────────────────────────────────────
    ("Complainant", "Citizen who files a complaint to open a case.", 1): [
        "view_case", "add_case",
        "view_casecomplainant",
        "view_notification", "change_notification",
    ],

    # ── Witness ─────────────────────────────────────────────────────
    ("Witness", "Citizen who has witnessed an incident.", 1): [
        "view_case",
        "view_notification", "change_notification",
    ],

    # ── Suspect ─────────────────────────────────────────────────────
    ("Suspect", "Individual identified as a suspect in a case.", 0): [
        "view_case",
        "view_bail",
        "view_notification", "change_notification",
    ],

    # ── Criminal ────────────────────────────────────────────────────
    ("Criminal", "Convicted individual — limited read-only access.", 0): [
        "view_case",
        "view_bail",
        "view_notification", "change_notification",
    ],

    # ── Base User ───────────────────────────────────────────────────
    ("Base User", "Default role for newly registered users before assignment.", 0): [
        "view_suspect",              # Most Wanted page is public
        "view_bountytip", "add_bountytip",
        "view_notification", "change_notification",
    ],
}


class Command(BaseCommand):
    help = (
        "Seeds the database with base Roles and maps them to Django "
        "permissions.  Safe to run multiple times (idempotent)."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n══════════════════════════════════════════"
            "\n  RBAC Setup — Seeding Roles & Permissions"
            "\n══════════════════════════════════════════\n"
        ))

        roles_created = 0
        roles_updated = 0

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
                # Update description and hierarchy_level if they differ
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
            resolved_permissions = []
            for codename in codenames:
                try:
                    perm = Permission.objects.get(codename=codename)
                    resolved_permissions.append(perm)
                except Permission.DoesNotExist:
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
        self.stdout.write(self.style.SUCCESS(
            f"  Done!  {roles_created} role(s) created, "
            f"{roles_updated} role(s) updated.  "
            f"Total: {roles_created + roles_updated} role(s).\n"
        ))
