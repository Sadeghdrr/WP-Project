from django.contrib import admin

from .models import (
    BiologicalEvidence,
    Evidence,
    EvidenceFile,
    IdentityEvidence,
    TestimonyEvidence,
    VehicleEvidence,
)


class EvidenceFileInline(admin.TabularInline):
    model = EvidenceFile
    extra = 0


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "evidence_type", "case",
                    "registered_by", "created_at")
    list_filter = ("evidence_type",)
    search_fields = ("title", "description")
    inlines = [EvidenceFileInline]


@admin.register(TestimonyEvidence)
class TestimonyEvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "case", "registered_by")


@admin.register(BiologicalEvidence)
class BiologicalEvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "case", "is_verified", "verified_by")
    list_filter = ("is_verified",)


@admin.register(VehicleEvidence)
class VehicleEvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "vehicle_model", "color",
                    "license_plate", "serial_number")


@admin.register(IdentityEvidence)
class IdentityEvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner_full_name", "case")


@admin.register(EvidenceFile)
class EvidenceFileAdmin(admin.ModelAdmin):
    list_display = ("id", "evidence", "file_type", "created_at")
    list_filter = ("file_type",)
