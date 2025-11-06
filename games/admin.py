from django.contrib import admin
from django.utils.html import format_html

from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "release_date", "is_featured", "admin_thumbnail")
    list_filter = ("status", "is_featured", "release_date")
    search_fields = ("title", "slug", "genre", "platforms")
    ordering = ("-is_featured", "-release_date", "title")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "preview_cover")
    fieldsets = (
        (None, {"fields": ("title", "slug", "tagline", "status", "is_featured")}),
        ("Conteúdo", {"fields": ("genre", "platforms", "short_description", "long_description", "trailer_url")}),
        (
            "Mídia",
            {
                "fields": (
                    "cover_image_upload",
                    "cover_image",
                    "hero_image_upload",
                    "preview_cover",
                )
            },
        ),
        ("Cronograma", {"fields": ("release_date",)}),
        ("Auditoria", {"fields": ("created_at", "updated_at")}),
    )

    def admin_thumbnail(self, obj):
        if obj.cover_image_url:
            return format_html('<img src="{}" style="height:48px;width:auto;border-radius:6px;" />', obj.cover_image_url)
        return "—"

    admin_thumbnail.short_description = "Capa"

    def preview_cover(self, obj):
        if obj.cover_image_url:
            return format_html('<img src="{}" style="max-height:200px;border-radius:12px;" />', obj.cover_image_url)
        return "Envie uma capa ou informe uma URL para visualizar aqui."

    preview_cover.short_description = "Pré-visualização"