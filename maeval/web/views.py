"""Server-rendered views for the human-facing web UI (see ADR-0006).

Read paths (home, list, search, detail, traces) are public. Write paths
(create submission, upvote) require a logged-in human principal — enforced by
``login_required`` and Django's session auth. Attribution (`author`,
`submitted_by_agent`) is derived from ``request.user``, never from posted data,
mirroring the API. Search and upvote reuse the shared model helpers
(`Submission.search`, `Vote.cast`) so behavior can't drift from the API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from maeval.accounts.models import ApiKey, User
from maeval.submissions.models import Submission, Vote
from maeval.traces.models import RunTrace
from maeval.web.forms import AgentForm, ApiKeyForm, SignupForm, SubmissionForm

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from django_htmx.middleware import HtmxDetails

    class HtmxHttpRequest(HttpRequest):
        """The request as seen by these views: HtmxMiddleware adds ``htmx``."""

        htmx: HtmxDetails


# Keep pages small; the catalog is human-scale (see ADR-0005).
PAGE_SIZE = 20

# A submission with at least this many upvotes but no run traces is flagged as
# *unmet demand* on the list — the demand↔ability gap the supply signal exists to
# surface (web.md FR-4b). Set to 1 so any public interest counts; tune upward if
# the flag gets noisy as the catalog grows.
UNMET_DEMAND_MIN_UPVOTES = 1


def _has_voted(request: HtmxHttpRequest, submission: Submission) -> bool:
    """Whether the logged-in principal has already upvoted ``submission``."""
    if not request.user.is_authenticated:
        return False
    principal = cast("User", request.user).principal
    return Vote.objects.filter(submission=submission, voter=principal).exists()


def home(request: HtmxHttpRequest) -> HttpResponse:
    """Landing page with the most-upvoted tasks as a teaser."""
    top = Submission.objects.order_by("-upvote_count", "-created_at").select_related("author")[:5]
    return render(request, "web/home.html", {"top_submissions": top})


def submission_list(request: HtmxHttpRequest) -> HttpResponse:
    """Browse + full-text search submissions, paginated.

    An htmx request (the live search box, pagination links) gets just the
    results fragment; a normal request gets the full page.
    """
    q = request.GET.get("q", "").strip()
    submissions = (
        Submission.search(q)
        .select_related("author")
        # Per-outcome trace tallies for the supply signal (web.md FR-4b). All four
        # are conditional aggregates over the one `traces` join, so this stays a
        # single query per page — no N+1 across the row's trace counts.
        .annotate(
            trace_count=Count("traces"),
            trace_success=Count("traces", filter=Q(traces__outcome=RunTrace.Outcome.SUCCESS)),
            trace_partial=Count("traces", filter=Q(traces__outcome=RunTrace.Outcome.PARTIAL)),
            trace_failed=Count("traces", filter=Q(traces__outcome=RunTrace.Outcome.FAILED)),
        )
    )
    page = Paginator(submissions, PAGE_SIZE).get_page(request.GET.get("page"))
    # The template flags a no-trace row as unmet demand at this threshold — the one
    # editorialized state (web.md FR-4b). Passed in rather than hard-coded in the
    # template so the rule lives next to the annotations that feed it.
    context = {"page_obj": page, "q": q, "unmet_demand_threshold": UNMET_DEMAND_MIN_UPVOTES}
    template = "web/_submission_list.html" if request.htmx else "web/submission_list.html"
    return render(request, template, context)


def submission_detail(request: HtmxHttpRequest, submission_id: str) -> HttpResponse:
    """One task, its upvote control, and the run traces recorded against it."""
    submission = get_object_or_404(Submission.objects.select_related("author"), pk=submission_id)
    traces = RunTrace.objects.filter(submission=submission).select_related("author")
    return render(
        request,
        "web/submission_detail.html",
        {"submission": submission, "traces": traces, "has_voted": _has_voted(request, submission)},
    )


@login_required
def submission_create(request: HtmxHttpRequest) -> HttpResponse:
    """Create a submission attributed to the logged-in human principal."""
    if request.method == "POST":
        form = SubmissionForm(request.POST)
        if form.is_valid():
            user = cast("User", request.user)
            submission = form.save(commit=False)
            submission.author = user
            submission.submitted_by_agent = user.is_agent
            submission.save()
            return redirect("web:submission_detail", submission_id=submission.pk)
    else:
        form = SubmissionForm()
    return render(request, "web/submission_form.html", {"form": form})


@require_POST
@login_required
def submission_upvote(request: HtmxHttpRequest, submission_id: str) -> HttpResponse:
    """Upvote a submission (idempotent); returns the refreshed upvote control."""
    submission = get_object_or_404(Submission, pk=submission_id)
    Vote.cast(submission=submission, caller=request.user)
    submission.refresh_from_db(fields=["upvote_count"])
    return render(request, "web/_upvote.html", {"submission": submission, "has_voted": True})


def trace_list(request: HtmxHttpRequest) -> HttpResponse:
    """All recorded run traces, newest first, paginated."""
    traces = RunTrace.objects.select_related("author", "submission")
    page = Paginator(traces, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "web/trace_list.html", {"page_obj": page})


def trace_detail(request: HtmxHttpRequest, trace_id: str) -> HttpResponse:
    """One run trace: its metadata and the recorded transcript, if any.

    A public read path (like the trace list). The transcript is rendered from
    the stored normalized steps (ADR-0011); a summary-only trace shows an empty
    state.
    """
    trace = get_object_or_404(RunTrace.objects.select_related("author", "submission"), pk=trace_id)
    return render(request, "web/trace_detail.html", {"trace": trace})


def llms_txt(request: HtmxHttpRequest) -> HttpResponse:
    """Serve ``/llms.txt`` (https://llmstxt.org): an LLM-oriented map of the site.

    Points agents at the human web surfaces and — the part that matters for them
    — the agent-facing API contract. Links are absolute (`build_absolute_uri`) so
    the file stays usable once fetched and passed around out of context.
    """
    context = {
        "home_url": request.build_absolute_uri(reverse("web:home")),
        "submissions_url": request.build_absolute_uri(reverse("web:submission_list")),
        "traces_url": request.build_absolute_uri(reverse("web:trace_list")),
        "signup_url": request.build_absolute_uri(reverse("web:signup")),
        "agents_url": request.build_absolute_uri(reverse("web:agent_list")),
        # The API mounts outside this URLconf (config/api.py); these paths are
        # Ninja/composition-root constants, not reversible `web:` names.
        "openapi_url": request.build_absolute_uri("/api/openapi.json"),
        "submissions_api_url": request.build_absolute_uri("/api/submissions/"),
        "traces_api_url": request.build_absolute_uri("/api/traces/"),
    }
    return render(request, "web/llms.txt", context, content_type="text/plain; charset=utf-8")


def signup(request: HtmxHttpRequest) -> HttpResponse:
    """Register a human principal and log them in."""
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Name the backend explicitly: django-axes adds a second entry to
            # AUTHENTICATION_BACKENDS, so `login()` can no longer infer which one
            # authenticated this freshly created human.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("web:submission_list")
    else:
        form = SignupForm()
    return render(request, "web/signup.html", {"form": form})


# --- agent + API-key management (ADR-0009) --------------------------------
#
# The browser self-serve surface for what the API also offers: a human registers
# agents and issues them scoped keys. Views reuse the model helpers
# (`User.create_agent`, `ApiKey.issue`, `ApiKey.revoke`) so behavior can't drift
# from the API. Ownership is scoped to `request.user` on every lookup — a human
# only ever sees or touches their own agents' keys.


@login_required
def agent_list(request: HtmxHttpRequest) -> HttpResponse:
    """List the logged-in human's agents and how many live keys each holds."""
    human = cast("User", request.user)
    now = timezone.now()
    live = Q(api_keys__revoked_at__isnull=True) & (
        Q(api_keys__expires_at__isnull=True) | Q(api_keys__expires_at__gt=now)
    )
    agents = (
        User.objects.filter(parent=human, is_agent=True)
        .annotate(
            key_count=Count("api_keys", distinct=True),
            active_key_count=Count("api_keys", filter=live, distinct=True),
            # Most recent authentication across all of the agent's keys; null
            # until one is used (last_used_at is stamped by ApiKeyAuth).
            last_active_at=Max("api_keys__last_used_at"),
        )
        .order_by("username")
    )
    return render(request, "web/agent_list.html", {"agents": agents})


@login_required
def agent_create(request: HtmxHttpRequest) -> HttpResponse:
    """Register an agent owned by the logged-in human."""
    human = cast("User", request.user)
    if request.method == "POST":
        form = AgentForm(request.POST)
        if form.is_valid():
            agent = User.create_agent(username=form.cleaned_data["username"], parent=human)
            messages.success(request, f"Agent “{agent.username}” registered.")
            return redirect("web:agent_detail", agent_id=agent.pk)
    else:
        form = AgentForm()
    return render(request, "web/agent_form.html", {"form": form})


def _get_owned_agent(request: HtmxHttpRequest, agent_id: str) -> User:
    """The caller's agent by id, or 404 — never another human's agent."""
    return get_object_or_404(User, pk=agent_id, parent=cast("User", request.user), is_agent=True)


@login_required
def agent_detail(request: HtmxHttpRequest, agent_id: str) -> HttpResponse:
    """One agent and its API keys (metadata only — secrets are never stored)."""
    agent = _get_owned_agent(request, agent_id)
    keys = ApiKey.objects.filter(agent=agent)  # ApiKey.Meta orders newest-first
    return render(request, "web/agent_detail.html", {"agent": agent, "keys": keys})


@login_required
def key_create(request: HtmxHttpRequest, agent_id: str) -> HttpResponse:
    """Issue a key for the caller's agent; show the raw token exactly once."""
    agent = _get_owned_agent(request, agent_id)
    if request.method == "POST":
        form = ApiKeyForm(request.POST)
        if form.is_valid():
            key, raw = ApiKey.issue(
                agent=agent,
                name=form.cleaned_data["name"],
                scopes=form.cleaned_data["scopes"],
                expires_at=form.cleaned_data["expires_at"],
            )
            # Rendered inline (not redirected): the raw secret lives only in this
            # one response and is never persisted or re-derivable.
            return render(
                request,
                "web/key_created.html",
                {"agent": agent, "key": key, "raw_key": raw},
            )
    else:
        form = ApiKeyForm()
    return render(request, "web/key_form.html", {"agent": agent, "form": form})


@require_POST
@login_required
def key_revoke(request: HtmxHttpRequest, key_id: str) -> HttpResponse:
    """Revoke one of the caller's keys (404 for a key that isn't theirs)."""
    key = get_object_or_404(
        ApiKey.objects.select_related("agent"),
        pk=key_id,
        agent__parent=cast("User", request.user),
    )
    key.revoke()
    messages.success(request, f"Key “{key.name}” revoked.")
    return redirect("web:agent_detail", agent_id=key.agent.pk)
