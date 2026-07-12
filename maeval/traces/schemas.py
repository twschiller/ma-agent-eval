"""Ninja I/O schemas for the traces app. Depends only on models."""

from ninja import Field, Schema

# Runtime (not type-only) import: `RunTrace.Outcome` is a pydantic field type
# below, so it must resolve at runtime — a TYPE_CHECKING block would break it.
from maeval.traces.models import RunTrace  # noqa: TC001


class TraceIn(Schema):
    """Create payload. `submitted_by_agent`/`author` are derived from the
    authenticated caller, never accepted from the body; `submission_id`
    identifies the task the run attempted."""

    submission_id: str
    model: str = Field(max_length=200)
    harness: str = Field(max_length=200)
    tools: list[str] = Field(default_factory=list)
    outcome: RunTrace.Outcome


class TraceOut(Schema):
    id: str
    submission_id: str
    model: str
    harness: str
    tools: list[str]
    outcome: RunTrace.Outcome
    submitted_by_agent: bool
    # Username of the reporting principal (the agent's own username for agent
    # traces), or None for author-less seed rows. Moderation deletes a
    # principal's traces outright (ADR-0004), so this does not go null on
    # removal — the row is gone.
    author: str | None = None

    @staticmethod
    def resolve_author(obj) -> str | None:
        return obj.author.username if obj.author_id else None
