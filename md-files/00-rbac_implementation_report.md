# RBAC Implementation Report

**Doer:** Sadegh Sargeran
**Date:** February 22, 2026

## Problem

The existing `accounts/models.py` implemented a custom `Role` model and a custom `User` model with a single ForeignKey to `Role`. However, it lacked the actual "Access Control" part of Role-Based Access Control (RBAC). Roles were just string labels, and there was no way to assign fine-grained permissions to them. We needed to integrate our custom `Role` model with Django's native permission system to allow checking permissions (e.g., `user.has_perm('cases.can_approve_case')`) instead of checking role names.

## Solution

1. **Imported Permission Model:** Imported `Permission` from `django.contrib.auth.models`.
2. **Updated Role Model:** Added a `ManyToManyField` named `permissions` to the `Role` model, linking it to Django's `Permission` model.
3. **Updated User Model:** Overrode the `has_perm`, `has_perms`, `has_module_perms`, and `get_all_permissions` methods on the custom `User` model to check if the requested permission exists within `self.role.permissions.all()`. Maintained compatibility with Django's superuser logic.
4. **Frontend Compatibility:** Added a `@property` named `permissions_list` to the `User` model that returns a flat list of permission codenames strings associated with the user's current role. This allows DRF serializers to pass a simple array of permissions to the Next.js frontend for dynamic UI rendering.
5. **Documentation:** Added a docstring to the `Role` model explaining how to define custom permissions in the `Meta` class of future models (e.g., `cases/models.py`) so they populate Django's `Permission` table.
