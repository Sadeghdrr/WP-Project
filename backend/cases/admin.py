from django.contrib import admin

from .models import Case, CaseComplainant, CaseStatusLog, CaseWitness


class CaseComplainantInline(admin.TabularInline):
    model = CaseComplainant
    extra = 0


class CaseWitnessInline(admin.TabularInline):
    model = CaseWitness
    extra = 0


class CaseStatusLogInline(admin.TabularInline):
    model = CaseStatusLog
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by",
                       "message", "created_at")


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "crime_level",
                    "creation_type", "created_at")
    list_filter = ("status", "crime_level", "creation_type")
    search_fields = ("title", "description")
    inlines = [CaseComplainantInline, CaseWitnessInline,
               CaseStatusLogInline]


@admin.register(CaseComplainant)
class CaseComplainantAdmin(admin.ModelAdmin):
    list_display = ("case", "user", "is_primary", "status")
    list_filter = ("status", "is_primary")


@admin.register(CaseWitness)
class CaseWitnessAdmin(admin.ModelAdmin):
    list_display = ("case", "full_name", "phone_number", "national_id")
    search_fields = ("full_name", "national_id")


@admin.register(CaseStatusLog)
class CaseStatusLogAdmin(admin.ModelAdmin):
    list_display = ("case", "from_status", "to_status",
                    "changed_by", "created_at")
    list_filter = ("to_status",)
