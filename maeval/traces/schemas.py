"""Ninja I/O schemas for the traces app. Depends only on models."""

from typing import Annotated, Any, Literal

from ninja import Field, Schema

# Runtime (not type-only) import: `RunTrace.Outcome` is a pydantic field type
# below, so it must resolve at runtime — a TYPE_CHECKING block would break it.
from maeval.traces.models import RunTrace  # noqa: TC001

# Upper bound on transcript length accepted at ingest. A guardrail on DB size,
# not a semantic limit — real runs are long, but not unbounded (ADR-0011). Over
# the cap is a `422`, not a silent truncation.
MAX_TRANSCRIPT_STEPS = 2000


# --- Transcript steps (ADR-0011) ------------------------------------------
#
# One trace's transcript is an ordered list of steps, each tagged by `kind`. The
# five kinds are a superset both Anthropic-shaped (Claude Code) and OpenAI-shaped
# (Codex) harnesses collapse onto; the client normalizes to them before
# submitting. The discriminated union below validates the shape on ingest — an
# unknown `kind` or a step missing its required fields is a `422`.


class UserStep(Schema):
    """A prompt/input turn from the human or environment driving the run."""

    kind: Literal["user"]
    content: str


class AssistantStep(Schema):
    """The agent's visible message text."""

    kind: Literal["assistant"]
    content: str


class ReasoningStep(Schema):
    """The agent's private reasoning / thinking, when the harness exposes it."""

    kind: Literal["reasoning"]
    content: str


class ToolCallStep(Schema):
    """A tool invocation: the tool name and its JSON input. `id` optionally
    pairs the call to its `tool_result` (a harness may instead just emit them
    adjacently)."""

    kind: Literal["tool_call"]
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None


class ToolResultStep(Schema):
    """The output of a tool call, flattened to a string, with an error flag.
    `tool_call_id` optionally pairs it back to its `tool_call`."""

    kind: Literal["tool_result"]
    output: str
    is_error: bool = False
    tool_call_id: str | None = None


TranscriptStep = Annotated[
    UserStep | AssistantStep | ReasoningStep | ToolCallStep | ToolResultStep,
    Field(discriminator="kind"),
]


class TraceIn(Schema):
    """Create payload. `submitted_by_agent`/`author` are derived from the
    authenticated caller, never accepted from the body; `submission_id`
    identifies the task the run attempted. `transcript` is **required and
    non-empty**: a trace is the evidence behind an outcome, so a run reported
    without its steps is rejected `422` (ADR-0011)."""

    submission_id: str
    model: str = Field(max_length=200)
    harness: str = Field(max_length=200)
    outcome: RunTrace.Outcome
    # No `tools` field: the tools a run used are derived server-side from the
    # transcript's `tool_call` steps (ADR-0011), not accepted from the body.
    transcript: list[TranscriptStep] = Field(min_length=1, max_length=MAX_TRANSCRIPT_STEPS)


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


class TraceDetailOut(TraceOut):
    """One trace *with* its transcript. The list endpoint returns the lean
    `TraceOut` (transcripts can be large); the detail endpoint returns this."""

    transcript: list[TranscriptStep] = Field(default_factory=list)
