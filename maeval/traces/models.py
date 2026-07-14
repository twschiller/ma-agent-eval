"""Run-trace domain models.

A *run trace* records one attempt by an AI agent (or a human reporting one) at a
:class:`~maeval.submissions.models.Submission` — which model, harness, and tools
were used, and whether the run succeeded. Traces are how the catalog turns from a
wish-list into an eval harness: they let the public see what agents can actually
do against a given civic task. See `docs/requirements/traces.md` for the
behavioral contract.
"""

import json
import re

from django.conf import settings
from django.db import models

from maeval.common.models import TimestampedModel
from maeval.submissions.models import Submission

# External links a run surfaced, for the "links checked in this run" breakout on
# the trace detail page. Only http(s): the schemes a transcript legitimately
# links out to (mirroring the render-time link allowlist, ADR-0012) and the only
# ones that name an external *site* a reader would visit. The character class
# stops at whitespace and the delimiters that bound a URL in prose/markup/JSON
# (quotes, backtick, closing brackets), so a link inside `(…)`, `"…"`, or a JSON
# string is captured without its wrapper.
_URL_RE = re.compile(r"https?://[^\s<>\"'`)\]}]+", re.IGNORECASE)
# Sentence punctuation a greedy match trails but that is almost never part of the
# link ("see https://x.gov/renew." -> drop the period).
_URL_TRAILING = ".,;:!?"


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
    # "claude-code").
    model = models.CharField(max_length=200)
    harness = models.CharField(max_length=200)
    # The distinct tool identifiers the run *used*. Derived at creation from the
    # transcript's `tool_call` steps (ADR-0011), never client-asserted — so it
    # can't disagree with the evidence. Stored (not computed on read) so the
    # lean list view has it without loading the transcript.
    tools = models.JSONField(default=list, blank=True)

    outcome = models.CharField(max_length=16, choices=Outcome.choices)

    # Optional normalized transcript of the run: an ordered list of steps
    # (`user` / `assistant` / `reasoning` / `tool_call` / `tool_result`),
    # submitted already-normalized by the client and stored verbatim (ADR-0011).
    # Empty for summary-only traces. The shape is validated on ingest by the API
    # (`schemas.TranscriptStep`), not by the DB. Public — a future ingest-time
    # scan will reject secrets/PII before a trace is accepted (`traces.md`).
    transcript = models.JSONField(default=list, blank=True)

    @staticmethod
    def tools_used(transcript: list[dict]) -> list[str]:
        """The distinct tool names invoked in a transcript, sorted. `tools` is
        derived from this at creation rather than client-asserted (ADR-0011)."""
        return sorted(
            {
                step["name"]
                for step in transcript
                if step.get("kind") == "tool_call" and step.get("name")
            }
        )

    @staticmethod
    def external_urls(transcript: list[dict]) -> list[str]:
        """Distinct external URLs surfaced in a transcript, in first-seen order.

        Pulls from what the run *checked* and what it *showed the user*:
        `tool_call` inputs, `tool_result` outputs, and `assistant` message text
        (not `user` prompts or private `reasoning`). Only http(s) — the links a
        reader would follow and the only schemes the render-time allowlist
        trusts (ADR-0012). Deduped with order preserved, so the list reads as the
        run's browsing trail. Powers the external-links breakout on the trace
        detail page, where following one is flagged as leaving the site."""
        urls: list[str] = []
        seen: set[str] = set()
        for step in transcript:
            kind = step.get("kind")
            if kind == "assistant":
                text = step.get("content", "")
            elif kind == "tool_result":
                text = step.get("output", "")
            elif kind == "tool_call":
                # Scan the JSON-serialized input so a URL nested anywhere in the
                # arguments is found; the `"` delimiters bound each match.
                text = json.dumps(step.get("input", {}), ensure_ascii=False)
            else:
                continue
            if not isinstance(text, str):  # defensive: seed rows bypass the schema
                continue
            for match in _URL_RE.finditer(text):
                url = match.group(0).rstrip(_URL_TRAILING)
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)
        return urls

    def __str__(self) -> str:
        return f"{self.model} ({self.outcome})"
