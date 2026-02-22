from django.contrib import admin

from .models import (
    Bail,
    BountyTip,
    Interrogation,
    Suspect,
    SuspectStatusLog,
    Trial,
    Warrant,
)


@admin.register(Suspect)
class SuspectAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "national_id", "status",
                    "case", "wanted_since")
    list_filter = ("status",)
    search_fields = ("full_name", "national_id")


@admin.register(Warrant)
class WarrantAdmin(admin.ModelAdmin):
    list_display = ("id", "suspect", "issued_by", "status", "issued_at")
    list_filter = ("status",)
    search_fields = ("reason",)


@admin.register(SuspectStatusLog)
class SuspectStatusLogAdmin(admin.ModelAdmin):
    list_display = ("id", "suspect", "from_status", "to_status",
                    "changed_by", "created_at")
    list_filter = ("from_status", "to_status")
    readonly_fields = ("suspect", "from_status", "to_status",
                       "changed_by", "notes", "created_at")


@admin.register(Interrogation)
class InterrogationAdmin(admin.ModelAdmin):
    list_display = ("id", "suspect", "case", "detective_guilt_score",
                    "sergeant_guilt_score", "created_at")


@admin.register(Trial)
class TrialAdmin(admin.ModelAdmin):
    list_display = ("id", "suspect", "case", "judge", "verdict",
                    "created_at")
    list_filter = ("verdict",)


@admin.register(BountyTip)
class BountyTipAdmin(admin.ModelAdmin):
    list_display = ("id", "informant", "suspect", "status",
                    "unique_code", "is_claimed")
    list_filter = ("status", "is_claimed")
    search_fields = ("unique_code",)


@admin.register(Bail)
class BailAdmin(admin.ModelAdmin):
    list_display = ("id", "suspect", "amount", "is_paid",
                    "approved_by", "paid_at")
    list_filter = ("is_paid",)
