"""Run-trace domain models.

A *run trace* records one attempt by an AI agent (or a human reporting one) at a
:class:`~maeval.submissions.models.Submission` — which model, harness, and tools
were used, and whether the run succeeded. Traces are how the catalog turns from a
wish-list into an eval harness: they let the public see what agents can actually
do against a given civic task. See `docs/requirements/traces.md` for the
behavioral contract.
"""

from django.conf import settings
from django.db import models

from maeval.common.models import TimestampedModel
from maeval.submissions.models import Submission


class RunTrace(TimestampedModel):
    """One recorded agent run against a submission, with its self-reported outcome."""

    class Outcome(models.TextChoices):
        # Judgment of how the run went, per BRIEF: success / partial / failure.
        SUCCESS = "success", "Successful"
        PARTIAL = "partial", "Partially successful"
        FAILED = "failed", "Failed"

    # The task-to-be-done this run attempted. A trace is meaningless without its
    # submission, so it is removed when the submission is.
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="traces")
    # The reporting principal. Set at creation from the authenticated caller; for
    # an agent it points at the agent user (whose username attributes the trace).
    # Deleting the principal cascades to its traces — how moderation removes a
    # bad actor's content (see ADR-0004). Nullable only for author-less rows
    # created directly (seed/tests), never via the API.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="traces",
    )
    # Distinguish a trace reported by an AI agent vs. a human principal. Derived
    # from the caller (`author.is_agent`), never asserted by the request body.
    submitted_by_agent = models.BooleanField(default=False)

    # What was run. Free-form strings: the space of models/harnesses is open and
    # evolves faster than any enum we'd maintain (e.g. "claude-opus-4-8",
    # "claude-code"). `tools` is the list of tool identifiers the run had access
    # to (e.g. MCP servers, function names).
    model = models.CharField(max_length=200)
    harness = models.CharField(max_length=200)
    tools = models.JSONField(default=list, blank=True)

    outcome = models.CharField(max_length=16, choices=Outcome.choices)

    def __str__(self) -> str:
        return f"{self.model} ({self.outcome})"
