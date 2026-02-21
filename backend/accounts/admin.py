from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "hierarchy_level", "description")
    search_fields = ("name",)
    ordering = ("-hierarchy_level",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "national_id", "phone_number",
                    "first_name", "last_name", "is_active", "role")
    search_fields = ("username", "email", "national_id", "phone_number")
    list_filter = ("is_active", "is_staff", "role")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Extra Info", {"fields": ("national_id", "phone_number", "role")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Extra Info", {"fields": ("email", "national_id", "phone_number",
                                   "first_name", "last_name", "role")}),
    )
