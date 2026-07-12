"""Ninja I/O schemas for the submissions app. Depends only on models."""

from ninja import Field, Schema


class SubmissionIn(Schema):
    """Create payload. `submitted_by_agent`/`author` are derived from the
    authenticated caller, never accepted from the body."""

    title: str = Field(max_length=200)
    description: str = ""


class SubmissionOut(Schema):
    id: str
    title: str
    description: str
    submitted_by_agent: bool
    upvote_count: int
    # Username of the authoring principal (the agent's own username for agent
    # content), or None for author-less seed rows. Moderation deletes a
    # principal's submissions outright (ADR-0004), so this does not go null on
    # removal — the row is gone.
    author: str | None = None

    @staticmethod
    def resolve_author(obj) -> str | None:
        return obj.author.username if obj.author_id else None
