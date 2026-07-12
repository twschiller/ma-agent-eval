"""Django-admin registrations for submissions. Part of the moderation surface
(ADR-0004): deleting an author cascades to their submissions; deleting a
submission cascades to its votes and traces."""

from django.contrib import admin

from maeval.submissions.models import Submission, Vote


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "submitted_by_agent", "upvote_count", "created_at")
    list_filter = ("submitted_by_agent",)
    search_fields = ("title", "description", "author__username")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("submission", "voter", "created_at")
    search_fields = ("submission__title", "voter__username")
