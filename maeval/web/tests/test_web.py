"""Tests for the server-rendered web UI (ADR-0006).

Covers the public read surface, htmx search/upvote fragments, and the
session-auth write paths. The API surface has its own tests; here we assert the
HTML layer and that attribution/vote semantics match via the shared helpers.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from maeval.accounts.models import ApiKey, User
from maeval.submissions.models import Submission, Vote
from maeval.traces.models import RunTrace

if TYPE_CHECKING:
    from pytest_django.fixtures import DjangoAssertNumQueries

PASSWORD = "corr3ct-horse-b4ttery"

# django-htmx reads this header to set `request.htmx`.
HTMX = {"HX-Request": "true"}


def list_url(**params: str) -> str:
    url = reverse("web:submission_list")
    return f"{url}?{urlencode(params)}" if params else url


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def human() -> User:
    return User.objects.create_user(username="alice", password=PASSWORD)


# --- public read surface --------------------------------------------------


@pytest.mark.django_db
def test_home_renders(client: Client) -> None:
    response = client.get(reverse("web:home"))
    assert response.status_code == 200
    assert b"MA Agent Eval" in response.content


@pytest.mark.django_db
def test_submission_list_shows_submissions(client: Client) -> None:
    Submission.objects.create(title="Renew my library card")
    response = client.get(reverse("web:submission_list"))
    assert response.status_code == 200
    assert b"Renew my library card" in response.content


@pytest.mark.django_db
def test_submission_list_htmx_returns_fragment(client: Client) -> None:
    Submission.objects.create(title="Renew my library card")
    response = client.get(list_url(), headers=HTMX)
    assert response.status_code == 200
    # The fragment has no <nav>/navbar chrome — just the results list.
    assert b"navbar" not in response.content
    assert b"Renew my library card" in response.content


@pytest.mark.django_db
def test_search_filters_by_query(client: Client) -> None:
    Submission.objects.create(title="Renew my library card")
    Submission.objects.create(title="Book a park pavilion")
    response = client.get(list_url(q="library"), headers=HTMX)
    assert b"library card" in response.content
    assert b"park pavilion" not in response.content


@pytest.mark.django_db
def test_search_no_match_shows_empty_state(client: Client) -> None:
    Submission.objects.create(title="Renew my library card")
    response = client.get(list_url(q="xyzzyplugh"), headers=HTMX)
    assert response.status_code == 200
    assert b"No tasks match" in response.content


@pytest.mark.django_db
def test_search_malformed_input_does_not_error(client: Client) -> None:
    # `websearch` parsing means hostile/sloppy input can't 500 the public box
    # (ADR-0005). It need not be empty — just not an error.
    Submission.objects.create(title="Renew my library card")
    for q in ['unbalanced " quote', "-", "a OR"]:
        response = client.get(list_url(q=q), headers=HTMX)
        assert response.status_code == 200


@pytest.mark.django_db
def test_detail_shows_submission_and_traces(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    RunTrace.objects.create(
        submission=submission,
        model="claude-opus-4-8",
        harness="claude-code",
        outcome=RunTrace.Outcome.SUCCESS,
    )
    response = client.get(reverse("web:submission_detail", args=[submission.pk]))
    assert response.status_code == 200
    assert b"claude-opus-4-8" in response.content
    assert b"Successful" in response.content


def _trace(submission: Submission, outcome: str) -> RunTrace:
    return RunTrace.objects.create(
        submission=submission, model="claude-opus-4-8", harness="claude-code", outcome=outcome
    )


@pytest.mark.django_db
def test_list_shows_supply_tally_for_traced_submission(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    for outcome in (RunTrace.Outcome.SUCCESS, RunTrace.Outcome.SUCCESS, RunTrace.Outcome.FAILED):
        _trace(submission, outcome)
    body = client.get(list_url(), headers=HTMX).content.decode()
    # The per-outcome breakdown and total, and the proportional bar's segments.
    assert 'aria-label="2 successful"' in body
    assert 'aria-label="1 failed"' in body
    assert "3 traces" in body
    assert "trace-bar__seg--success" in body
    assert "trace-bar__seg--failed" in body
    # No partial traces → no partial segment or chip (zeros are omitted, not shown).
    assert "trace-bar__seg--partial" not in body
    assert "partial" not in body


@pytest.mark.django_db
def test_list_flags_unmet_demand(client: Client) -> None:
    # Demand exists, but no agent has attempted it — the one editorialized state.
    Submission.objects.create(title="Get a food truck permit", upvote_count=3)
    body = client.get(list_url(), headers=HTMX).content.decode()
    assert "supply--gap" in body
    assert "No traces yet" in body


@pytest.mark.django_db
def test_list_does_not_flag_when_no_demand(client: Client) -> None:
    # No demand and no traces → quiet empty state, never the amber gap flag.
    Submission.objects.create(title="Obscure task nobody wants", upvote_count=0)
    body = client.get(list_url(), headers=HTMX).content.decode()
    assert "supply--empty" in body
    assert "supply--gap" not in body


@pytest.mark.django_db
def test_list_does_not_flag_traced_submission(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card", upvote_count=5)
    _trace(submission, RunTrace.Outcome.SUCCESS)
    body = client.get(list_url(), headers=HTMX).content.decode()
    # Demand met by a trace — no gap flag, and the tally shows instead.
    assert "supply--gap" not in body
    assert 'aria-label="1 successful"' in body


@pytest.mark.django_db
def test_list_supply_counts_do_not_n_plus_one(
    client: Client, django_assert_max_num_queries: DjangoAssertNumQueries
) -> None:
    # Trace tallies come from one annotated aggregate query, so query count must
    # not scale with the number of rows or their traces (web.md FR-4b).
    for i in range(5):
        submission = Submission.objects.create(title=f"Task {i}", upvote_count=i)
        for outcome in (RunTrace.Outcome.SUCCESS, RunTrace.Outcome.PARTIAL):
            _trace(submission, outcome)
    with django_assert_max_num_queries(6):
        client.get(list_url(), headers=HTMX)


@pytest.mark.django_db
def test_agent_content_is_badged(client: Client) -> None:
    submission = Submission.objects.create(title="Agent task", submitted_by_agent=True)
    response = client.get(reverse("web:submission_detail", args=[submission.pk]))
    assert b"agent" in response.content


@pytest.mark.django_db
def test_home_links_to_llms_txt(client: Client) -> None:
    response = client.get(reverse("web:home"))
    assert reverse("web:llms_txt") in response.content.decode()


def test_llms_txt_served_as_plain_text(client: Client) -> None:
    response = client.get(reverse("web:llms_txt"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    body = response.content.decode()
    # The llms.txt standard: an H1 title, then a `>` summary blockquote.
    assert body.startswith("# MA Agent Eval\n")
    assert "\n> " in body
    # Points agents at the API contract with an absolute link.
    assert "http://testserver/api/openapi.json" in body
    # ...and at where they mint the API keys that contract requires (ADR-0009).
    assert "http://testserver" + reverse("web:agent_list") in body
    assert "http://testserver" + reverse("web:signup") in body
    # The run-trace quickstart: an agent can record a trace without first
    # parsing the schema — the write endpoint, its scope, required transcript,
    # derived tools, and the outcome enum.
    assert "http://testserver/api/traces/" in body
    assert "http://testserver/api/submissions/" in body
    assert "traces:write" in body
    assert "outcome" in body
    assert '"transcript"' in body
    assert "Do not send `tools`" in body
    assert '"kind": "tool_call"' in body
    assert "GET /api/traces/{id}" in body
    assert "do not click final submit" in body


# --- auth-gated write paths ----------------------------------------------


@pytest.mark.django_db
def test_create_requires_login(client: Client) -> None:
    response = client.get(reverse("web:submission_create"))
    assert response.status_code == 302
    assert reverse("web:login") in response.headers["Location"]


@pytest.mark.django_db
def test_create_submission_attributes_to_human(client: Client, human: User) -> None:
    client.force_login(human)
    response = client.post(
        reverse("web:submission_create"),
        {"title": "Draft a block-party permit", "description": ""},
    )
    assert response.status_code == 302
    submission = Submission.objects.get(title="Draft a block-party permit")
    assert submission.author == human
    assert submission.submitted_by_agent is False


@pytest.mark.django_db
def test_upvote_requires_login(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    response = client.post(reverse("web:submission_upvote", args=[submission.pk]))
    assert response.status_code == 302
    assert reverse("web:login") in response.headers["Location"]


@pytest.mark.django_db
def test_upvote_increments_and_is_idempotent(client: Client, human: User) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    client.force_login(human)
    url = reverse("web:submission_upvote", args=[submission.pk])

    first = client.post(url)
    assert first.status_code == 200
    submission.refresh_from_db()
    assert submission.upvote_count == 1

    # A repeat upvote by the same principal does not inflate the count.
    client.post(url)
    submission.refresh_from_db()
    assert submission.upvote_count == 1
    assert Vote.objects.filter(submission=submission).count() == 1


@pytest.mark.django_db
def test_upvote_is_get_safe(client: Client, human: User) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    client.force_login(human)
    response = client.get(reverse("web:submission_upvote", args=[submission.pk]))
    assert response.status_code == 405


# --- account flows --------------------------------------------------------


@pytest.mark.django_db
def test_signup_creates_human_and_logs_in(client: Client) -> None:
    response = client.post(
        reverse("web:signup"),
        {"username": "bob", "password1": PASSWORD, "password2": PASSWORD},
    )
    assert response.status_code == 302
    user = User.objects.get(username="bob")
    assert user.is_agent is False
    assert user.parent is None
    # Session cookie established (logged in).
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_signup_rejects_duplicate_username(client: Client) -> None:
    User.objects.create_user(username="bob", password=PASSWORD)
    response = client.post(
        reverse("web:signup"),
        {"username": "bob", "password1": PASSWORD, "password2": PASSWORD},
    )
    # Form re-renders with an error rather than creating a second account.
    assert response.status_code == 200
    assert User.objects.filter(username="bob").count() == 1
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_signup_rejects_weak_password(client: Client) -> None:
    response = client.post(
        reverse("web:signup"),
        {"username": "bob", "password1": "123", "password2": "123"},
    )
    # Django's AUTH_PASSWORD_VALIDATORS reject the weak password; form re-renders.
    assert response.status_code == 200
    assert not User.objects.filter(username="bob").exists()
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@override_settings(SIGNUP_INVITE_CODE="let-me-in")
def test_signup_requires_invite_code_when_set(client: Client) -> None:
    response = client.post(
        reverse("web:signup"),
        {"username": "bob", "password1": PASSWORD, "password2": PASSWORD},
    )
    # No code supplied while the gate is on: form re-renders, no account created.
    assert response.status_code == 200
    assert not User.objects.filter(username="bob").exists()
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@override_settings(SIGNUP_INVITE_CODE="let-me-in")
def test_signup_rejects_wrong_invite_code(client: Client) -> None:
    response = client.post(
        reverse("web:signup"),
        {
            "username": "bob",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "invite_code": "nope",
        },
    )
    assert response.status_code == 200
    assert not User.objects.filter(username="bob").exists()


@pytest.mark.django_db
@override_settings(SIGNUP_INVITE_CODE="let-me-in")
def test_signup_accepts_correct_invite_code(client: Client) -> None:
    response = client.post(
        reverse("web:signup"),
        {
            "username": "bob",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "invite_code": "let-me-in",
        },
    )
    assert response.status_code == 302
    assert User.objects.filter(username="bob").exists()
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_login_flow(client: Client, human: User) -> None:
    response = client.post(reverse("web:login"), {"username": "alice", "password": PASSWORD})
    assert response.status_code == 302
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_admin_login_redirects_to_primary_login(client: Client) -> None:
    # The admin has no login form of its own (web.md FR-1): visiting it sends the
    # caller to the primary session login, preserving `next` so they return.
    response = client.get("/admin/login/", {"next": "/admin/submissions/"})
    assert response.status_code == 302
    location = response.headers["Location"]
    assert location.startswith(reverse("web:login"))
    assert "next=/admin/submissions/" in location


# --- agent + API-key management (ADR-0009) --------------------------------


@pytest.mark.django_db
def test_agent_management_requires_login(client: Client) -> None:
    # The whole management surface is login-gated; the list stands in for it.
    response = client.get(reverse("web:agent_list"))
    assert response.status_code == 302
    assert reverse("web:login") in response.headers["Location"]


@pytest.mark.django_db
def test_create_agent_from_browser_links_to_human(client: Client, human: User) -> None:
    client.force_login(human)
    response = client.post(reverse("web:agent_create"), {"username": "alice-bot"})
    assert response.status_code == 302
    agent = User.objects.get(username="alice-bot")
    assert agent.is_agent is True
    assert agent.parent == human
    # Redirects to the new agent's page.
    assert response.headers["Location"] == reverse("web:agent_detail", args=[agent.pk])


@pytest.mark.django_db
def test_agent_list_shows_only_own_agents(client: Client, human: User) -> None:
    mine = User.create_agent(username="mine-bot", parent=human)
    other_human = User.objects.create_user(username="bob", password=PASSWORD)
    User.create_agent(username="bob-bot", parent=other_human)
    client.force_login(human)
    response = client.get(reverse("web:agent_list"))
    assert response.status_code == 200
    assert b"mine-bot" in response.content
    assert b"bob-bot" not in response.content
    assert mine  # referenced for clarity


@pytest.mark.django_db
def test_agent_list_shows_last_active(client: Client, human: User) -> None:
    agent = User.create_agent(username="alice-bot", parent=human)
    _key, raw = ApiKey.issue(agent=agent, name="ci", scopes=[])
    client.force_login(human)

    # No key used yet: the agent reads "never used".
    assert b"never used" in client.get(reverse("web:agent_list")).content

    # After the key authenticates, the row shows a relative "last used … ago".
    assert (
        client.get("/api/accounts/me", headers={"authorization": f"Bearer {raw}"}).status_code
        == 200
    )
    body = client.get(reverse("web:agent_list")).content
    assert b"last used" in body
    assert b"never used" not in body


@pytest.mark.django_db
def test_issue_key_shows_raw_once_and_stores_hash(client: Client, human: User) -> None:
    agent = User.create_agent(username="alice-bot", parent=human)
    client.force_login(human)
    response = client.post(
        reverse("web:key_create", args=[agent.pk]),
        {"name": "laptop", "scopes": ["submissions:write"]},
    )
    assert response.status_code == 200
    key = ApiKey.objects.get(agent=agent, name="laptop")
    raw = f"mae_{key.prefix}_"
    # The raw token is present in this one response...
    assert raw.encode() in response.content
    # ...and it resolves, while only the hash is stored.
    body = response.content.decode()
    start = body.index(f"mae_{key.prefix}_")
    token = body[start : start + 4 + len(key.prefix) + 1 + 64]
    assert ApiKey.resolve(token) == key
    assert token.split("_")[2] not in key.hashed_secret


@pytest.mark.django_db
def test_issue_key_rejects_past_expiry(client: Client, human: User) -> None:
    agent = User.create_agent(username="alice-bot", parent=human)
    client.force_login(human)
    yesterday = (timezone.now() - timedelta(days=1)).date().isoformat()
    response = client.post(
        reverse("web:key_create", args=[agent.pk]),
        {"name": "laptop", "scopes": [], "expires_at": yesterday},
    )
    # Form re-renders with an error; no key created.
    assert response.status_code == 200
    assert not ApiKey.objects.filter(agent=agent).exists()


@pytest.mark.django_db
def test_cannot_issue_key_for_foreign_agent(client: Client, human: User) -> None:
    bob = User.objects.create_user(username="bob", password=PASSWORD)
    bob_bot = User.create_agent(username="bob-bot", parent=bob)
    client.force_login(human)
    response = client.post(
        reverse("web:key_create", args=[bob_bot.pk]),
        {"name": "steal", "scopes": []},
    )
    assert response.status_code == 404
    assert not ApiKey.objects.filter(agent=bob_bot).exists()


@pytest.mark.django_db
def test_key_detail_shows_last_used(client: Client, human: User) -> None:
    agent = User.create_agent(username="alice-bot", parent=human)
    # An expiry so the Expires cell shows a date — the only "Never" left on the
    # page is then the last-used cell, which we can assert on unambiguously.
    _key, raw = ApiKey.issue(
        agent=agent, name="ci", scopes=[], expires_at=timezone.now() + timedelta(days=30)
    )
    client.force_login(human)
    detail_url = reverse("web:agent_detail", args=[agent.pk])

    # A key that has never authenticated reads "Never".
    assert b"Never" in client.get(detail_url).content

    # Using the key over the API stamps last_used_at (auth.py); the page then
    # shows a relative "… ago" and no longer "Never".
    used = client.get("/api/accounts/me", headers={"authorization": f"Bearer {raw}"})
    assert used.status_code == 200
    after = client.get(detail_url).content
    assert b"ago" in after
    assert b"Never" not in after


@pytest.mark.django_db
def test_revoke_key_from_browser(client: Client, human: User) -> None:
    agent = User.create_agent(username="alice-bot", parent=human)
    key, raw = ApiKey.issue(agent=agent, name="ci", scopes=[])
    client.force_login(human)
    response = client.post(reverse("web:key_revoke", args=[key.pk]))
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("web:agent_detail", args=[agent.pk])
    key.refresh_from_db()
    assert key.revoked_at is not None
    assert ApiKey.resolve(raw) is None


@pytest.mark.django_db
def test_cannot_revoke_foreign_key(client: Client, human: User) -> None:
    bob = User.objects.create_user(username="bob", password=PASSWORD)
    bob_bot = User.create_agent(username="bob-bot", parent=bob)
    key, raw = ApiKey.issue(agent=bob_bot, name="ci", scopes=[])
    client.force_login(human)
    response = client.post(reverse("web:key_revoke", args=[key.pk]))
    assert response.status_code == 404
    key.refresh_from_db()
    assert key.revoked_at is None
    assert ApiKey.resolve(raw) == key


@pytest.mark.django_db
def test_revoke_is_post_only(client: Client, human: User) -> None:
    agent = User.create_agent(username="alice-bot", parent=human)
    key, _raw = ApiKey.issue(agent=agent, name="ci", scopes=[])
    client.force_login(human)
    response = client.get(reverse("web:key_revoke", args=[key.pk]))
    assert response.status_code == 405


@pytest.mark.django_db
def test_account_menu_links_to_key_management(client: Client, human: User) -> None:
    client.force_login(human)
    response = client.get(reverse("web:home"))
    body = response.content.decode()
    assert reverse("web:agent_list") in body
    assert "API keys" in body


@pytest.mark.django_db
def test_trace_list_renders(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    RunTrace.objects.create(
        submission=submission,
        model="claude-opus-4-8",
        harness="claude-code",
        outcome=RunTrace.Outcome.PARTIAL,
    )
    response = client.get(reverse("web:trace_list"))
    assert response.status_code == 200
    assert b"claude-opus-4-8" in response.content
    assert b"Partially successful" in response.content


@pytest.mark.django_db
def test_trace_list_links_to_detail(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    trace = RunTrace.objects.create(
        submission=submission, model="m", harness="h", outcome=RunTrace.Outcome.SUCCESS
    )
    body = client.get(reverse("web:trace_list")).content.decode()
    assert reverse("web:trace_detail", args=[trace.pk]) in body


@pytest.mark.django_db
def test_trace_detail_renders_transcript(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    trace = RunTrace.objects.create(
        submission=submission,
        model="claude-opus-4-8",
        harness="claude-code",
        outcome=RunTrace.Outcome.SUCCESS,
        transcript=[
            {"kind": "user", "content": "Renew my library card"},
            {"kind": "reasoning", "content": "check the catalog first"},
            {"kind": "assistant", "content": "Looking up your account"},
            {"kind": "tool_call", "name": "library-mcp.lookup", "input": {"card": "123"}},
            {"kind": "tool_result", "output": "Account found", "is_error": False},
        ],
    )
    response = client.get(reverse("web:trace_detail", args=[trace.pk]))
    assert response.status_code == 200
    body = response.content.decode()
    # Metadata + every step kind's content is rendered.
    assert "claude-opus-4-8" in body
    assert "check the catalog first" in body  # reasoning
    assert "Looking up your account" in body  # assistant
    assert "library-mcp.lookup" in body  # tool call name
    assert "Account found" in body  # tool result output


@pytest.mark.django_db
def test_trace_detail_flags_error_tool_result(client: Client) -> None:
    submission = Submission.objects.create(title="Book a park")
    trace = RunTrace.objects.create(
        submission=submission,
        model="m",
        harness="h",
        outcome=RunTrace.Outcome.FAILED,
        transcript=[{"kind": "tool_result", "output": "boom", "is_error": True}],
    )
    body = client.get(reverse("web:trace_detail", args=[trace.pk])).content.decode()
    assert "trace-code--error" in body


@pytest.mark.django_db
def test_trace_detail_empty_state_without_transcript(client: Client) -> None:
    submission = Submission.objects.create(title="Book a park")
    trace = RunTrace.objects.create(
        submission=submission, model="m", harness="h", outcome=RunTrace.Outcome.SUCCESS
    )
    response = client.get(reverse("web:trace_detail", args=[trace.pk]))
    assert response.status_code == 200
    assert b"No transcript recorded" in response.content


@pytest.mark.django_db
def test_trace_detail_unknown_id_is_404(client: Client) -> None:
    assert client.get(reverse("web:trace_detail", args=["NOTAREALID"])).status_code == 404


# --- Content-Security-Policy (ADR-0010) ---------------------------------------


@pytest.mark.django_db
def test_response_carries_strict_csp_header(client: Client) -> None:
    response = client.get(reverse("web:home"))
    csp = response.headers["Content-Security-Policy"]
    # Strict same-origin: no `unsafe-*`, script/style locked to `'self'`.
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "unsafe-" not in csp


@pytest.mark.django_db
def test_templates_carry_no_inline_script(client: Client, human: User) -> None:
    """Inline `<script>` / `on*=` handlers would need `unsafe-inline`; the CSP
    forbids it, so behavior must live in static files. Guards the whole rendered
    surface a logged-in user touches for the key flows."""
    agent = User.create_agent(username="alice-bot", parent=human)
    ApiKey.issue(agent=agent, name="ci", scopes=[])
    client.force_login(human)
    for name, args in [
        ("web:home", []),  # base.html: account-menu + confirm-submit scripts
        ("web:agent_detail", [agent.pk]),  # was inline `onsubmit` on revoke
        ("web:key_create", [agent.pk]),  # was inline expiry-preset script
    ]:
        body = client.get(reverse(name, args=args)).content.decode()
        assert "<script>" not in body, name
        assert "onsubmit=" not in body, name
