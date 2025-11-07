from django.contrib import admin
from django.utils.html import format_html

from .models import DonationPledge, EmailVerification, FAQCategory, FAQEntry, Feedback, Game


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


class FAQEntryInline(admin.StackedInline):
    model = FAQEntry
    extra = 1
    fields = ("question", "answer", "audience", "order", "is_featured", "is_active")


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "description")
    ordering = ("order", "title")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [FAQEntryInline]


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "audience", "order", "is_featured", "is_active")
    list_filter = ("category", "audience", "is_featured", "is_active")
    search_fields = ("question", "answer")
    ordering = ("category", "order")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "topic", "impact_rating", "status", "is_public", "created_at")
    list_filter = ("status", "topic", "is_public", "created_at")
    search_fields = ("title", "message", "user__username", "user__email")
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(DonationPledge)
class DonationPledgeAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "currency", "pix_status", "is_recurring", "created_at")
    list_filter = ("pix_status", "is_recurring", "visibility", "currency", "created_at")
    search_fields = ("user__username", "user__email", "message", "pix_txid", "pix_transaction_code")
    ordering = ("-created_at",)
    autocomplete_fields = ("user",)
    readonly_fields = ("pix_txid", "pix_last_checked_at")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "expires_at", "verified_at", "attempts")
    list_filter = ("created_at", "verified_at")
    search_fields = ("user__username", "user__email", "code")
    ordering = ("-created_at",)