from django.contrib import admin

from .models import BoardConnection, BoardItem, BoardNote, DetectiveBoard


class BoardItemInline(admin.TabularInline):
    model = BoardItem
    extra = 0


class BoardConnectionInline(admin.TabularInline):
    model = BoardConnection
    extra = 0


@admin.register(DetectiveBoard)
class DetectiveBoardAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "detective", "created_at")
    inlines = [BoardItemInline, BoardConnectionInline]


@admin.register(BoardNote)
class BoardNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "board", "created_by")
    search_fields = ("title", "content")


@admin.register(BoardItem)
class BoardItemAdmin(admin.ModelAdmin):
    list_display = ("id", "board", "content_type", "object_id",
                    "position_x", "position_y")


@admin.register(BoardConnection)
class BoardConnectionAdmin(admin.ModelAdmin):
    list_display = ("id", "board", "from_item", "to_item")
