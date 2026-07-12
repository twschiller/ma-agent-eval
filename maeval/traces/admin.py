"""Django-admin registration for run traces. Part of the moderation surface
(ADR-0004): deleting an author cascades to their traces."""

from django.contrib import admin

from maeval.traces.models import RunTrace


@admin.register(RunTrace)
class RunTraceAdmin(admin.ModelAdmin):
    list_display = ("model", "harness", "outcome", "submission", "author", "created_at")
    list_filter = ("outcome", "submitted_by_agent")
    search_fields = ("model", "harness", "submission__title", "author__username")
