"""Django-admin registrations for identity models.

The admin is the moderation surface (ADR-0004): a staff user finds a human
principal here and deletes it. That delete cascades to the human's agents (via
``parent``), their API keys, and — because content ``author`` FKs cascade — all
submissions, traces, and votes authored by the human or its agents. No custom
moderation endpoint exists; the built-in delete confirmation is the review step.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from maeval.accounts.models import ApiKey, User


@admin.register(User)
class PrincipalAdmin(UserAdmin):
    """Human + agent principals. Deleting a human cascades to its agents."""

    list_display = ("username", "is_agent", "parent", "is_staff", "is_active")
    list_filter = ("is_agent", "is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("username",)
    # `parent` and `is_agent` are set by the identity layer, not hand-edited.
    readonly_fields = ("is_agent", "parent")
    # Append the principal-kind fields to Django's stock UserAdmin layout.
    fieldsets = (
        *(UserAdmin.fieldsets or ()),
        ("Principal", {"fields": ("is_agent", "parent")}),
    )


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    """Read-only view of issued keys; secrets are never shown (hash-only)."""

    list_display = (
        "name",
        "agent",
        "prefix",
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
    )
    search_fields = ("name", "prefix", "agent__username")
    readonly_fields = ("prefix", "hashed_secret", "scopes", "created_at", "last_used_at")
