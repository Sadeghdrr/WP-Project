"""
Accounts app models.

Defines the dynamic Role system and a custom User model that extends
Django's ``AbstractUser``.  Every field aligns with the project-doc
requirements (unique national-ID, phone, email; dynamic single-role
assignment; hierarchy levels for police ranks).
"""

from django.contrib.auth.models import AbstractUser, Permission
from django.db import models

from core.permissions_constants import AccountsPerms


class Role(models.Model):
    """
    Dynamic, admin-manageable role.

    Roles can be created, modified, or deleted at runtime by the System
    Administrator — no code changes required.  ``hierarchy_level`` encodes
    the relative power within the police hierarchy (e.g. Police Chief > Captain
    > Sergeant > Detective > Patrol Officer > Cadet).

    Default roles seeded via data-migration / fixture:
        System Admin, Police Chief, Captain, Sergeant, Detective,
        Police Officer, Cadet, Coroner, Judge, Base User.

    Note on Custom Permissions:
    Custom workflow permissions are defined as constants in
    ``core.permissions_constants`` and registered in each model's
    ``Meta.permissions`` tuple using those constants. For example::

        from core.permissions_constants import CasesPerms
        class Meta:
            permissions = [
                (CasesPerms.CAN_APPROVE_CASE, "Can approve case closure"),
            ]

    Running ``makemigrations`` and ``migrate`` populates Django's
    ``auth_permission`` table.  The ``setup_rbac`` management command
    then links these permissions to ``Role`` objects — it never
    creates permissions itself.
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
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        verbose_name="Permissions",
        help_text="Specific permissions for this role.",
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
        permissions = [
            (AccountsPerms.CAN_MANAGE_USERS, "Admin-level user management"),
        ]

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

    # ── RBAC Permission Overrides ────────────────────────────────────

    def get_all_permissions(self, obj=None) -> set:
        """
        Return a set of permission strings ('app_label.codename') the user has.
        """
        if not self.is_active:
            return set()
            
        if self.is_superuser:
            if not hasattr(self, '_superuser_perm_cache'):
                perms = Permission.objects.select_related('content_type').all()
                self._superuser_perm_cache = {f"{p.content_type.app_label}.{p.codename}" for p in perms}
            return self._superuser_perm_cache

        if not self.role:
            return set()
            
        if not hasattr(self, '_perm_cache'):
            perms = self.role.permissions.select_related('content_type')
            self._perm_cache = {f"{p.content_type.app_label}.{p.codename}" for p in perms}
            
        return self._perm_cache

    def has_perm(self, perm: str, obj=None) -> bool:
        """
        Check if the user has a specific permission.
        Superusers always have all permissions.
        Otherwise, check if the assigned role has the permission.
        """
        if self.is_active and self.is_superuser:
            return True
            
        return perm in self.get_all_permissions(obj)

    def has_perms(self, perm_list, obj=None) -> bool:
        """
        Check if the user has all permissions in the given list.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label: str) -> bool:
        """
        Check if the user has any permissions in the given app label.
        """
        if self.is_active and self.is_superuser:
            return True
            
        return any(perm.startswith(f"{app_label}.") for perm in self.get_all_permissions())

    @property
    def permissions_list(self) -> list[str]:
        """
        Return a flat list of permission codenames strings associated with the user's role.
        Useful for DRF serializers to pass to the frontend for dynamic UI rendering.
        """
        return list(self.get_all_permissions())
