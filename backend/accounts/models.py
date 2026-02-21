"""
Accounts app models.

Defines the dynamic Role system and a custom User model that extends
Django's ``AbstractUser``.  Every field aligns with the project-doc
requirements (unique national-ID, phone, email; dynamic single-role
assignment; hierarchy levels for police ranks).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    """
    Dynamic, admin-manageable role.

    Roles can be created, modified, or deleted at runtime by the System
    Administrator — no code changes required.  ``hierarchy_level`` encodes
    the relative power within the police hierarchy (e.g. Police Chief > Captain
    > Sergeant > Detective > Patrol Officer > Cadet).

    Default roles seeded via data-migration / fixture:
        System Admin, Police Chief, Captain, Sergeant, Detective,
        Police Officer, Patrol Officer, Cadet, Coroner, Judge,
        Complainant, Witness, Suspect, Criminal, Base User.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Role Name",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )
    hierarchy_level = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Hierarchy Level",
        help_text="Higher value = more authority (e.g. Chief=10, Cadet=1).",
    )

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["-hierarchy_level"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom user model for the L.A. Noire police-department system.

    Registration requires at minimum: username, password, email,
    phone_number, first_name, last_name, and national_id.
    Login is supported via *any one* of username / national_id /
    phone_number / email together with the password.

    Each user holds exactly **one** role at a time (FK to ``Role``).
    New users register as "Base User"; the System Administrator then
    assigns the appropriate role.
    """

    national_id = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="National ID",
        help_text="Unique 10-digit Iranian national identification number.",
        db_index=True,
    )
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Phone Number",
        db_index=True,
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email Address",
    )

    # ── Single-role assignment (dynamic RBAC) ────────────────────────
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Assigned Role",
    )

    # Fields required when creating a superuser via CLI
    REQUIRED_FIELDS = ["email", "national_id", "phone_number",
                       "first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        role_name = self.role.name if self.role else "No Role"
        return f"{self.username} ({self.get_full_name()}) - {role_name}"

    # ── Helper predicates for role checks ────────────────────────────

    def has_role(self, role_name: str) -> bool:
        """Check if the user's current role matches the given name."""
        return self.role is not None and self.role.name == role_name

    @property
    def hierarchy_level(self) -> int:
        """Return the hierarchy_level of the user's role (0 if none)."""
        return self.role.hierarchy_level if self.role else 0
