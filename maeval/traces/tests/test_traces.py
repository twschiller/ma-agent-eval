"""Tests for the run-traces API: public list (with filter) and scoped create."""

import base64

import pytest
from django.test import Client

from maeval.accounts.models import SCOPE_TRACES_WRITE, ApiKey, User
from maeval.submissions.models import Submission
from maeval.traces.models import RunTrace
from maeval.traces.schemas import MAX_TRANSCRIPT_STEPS

PASSWORD = "corr3ct-horse-b4ttery"

# A normalized transcript covering all five step kinds (ADR-0011).
TRANSCRIPT = [
    {"kind": "user", "content": "Renew my library card"},
    {"kind": "reasoning", "content": "I'll check the catalog API first."},
    {"kind": "assistant", "content": "Looking up your account."},
    {"kind": "tool_call", "name": "library-mcp.lookup", "input": {"card": "123"}, "id": "c1"},
    {"kind": "tool_result", "output": "Account found", "is_error": False, "tool_call_id": "c1"},
]


@pytest.fixture
def client() -> Client:
    return Client()


def basic(username: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"authorization": f"Basic {raw}"}


def bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def agent_key(human: User, *, name: str, scopes: list[str]) -> str:
    agent = User.create_agent(username=f"{human.username}-bot", parent=human)
    _key, raw = ApiKey.issue(agent=agent, name=name, scopes=scopes)
    return raw


def payload(submission: Submission, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "submission_id": submission.pk,
        "model": "claude-opus-4-8",
        "harness": "claude-code",
        "outcome": "success",
        # `transcript` is required (ADR-0011); a minimal one keeps the shared
        # helper valid. Tests exercising the transcript override it. `tools` is
        # not sent — it is derived from the transcript's tool calls.
        "transcript": [{"kind": "user", "content": "Renew my library card"}],
    }
    body.update(overrides)
    return body


# --- public list ----------------------------------------------------------


@pytest.mark.django_db
def test_list_traces_empty(client: Client) -> None:
    response = client.get("/api/traces/")
    assert response.status_code == 200
    # LimitOffset page envelope, empty (FR-1).
    assert response.json() == {"items": [], "count": 0}


@pytest.mark.django_db
def test_list_traces_returns_created(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    RunTrace.objects.create(
        submission=submission,
        model="claude-opus-4-8",
        harness="claude-code",
        tools=["library-mcp"],
        outcome=RunTrace.Outcome.PARTIAL,
    )
    response = client.get("/api/traces/")
    body = response.json()
    assert body["count"] == 1
    items = body["items"]
    assert len(items) == 1
    assert items[0]["model"] == "claude-opus-4-8"
    assert items[0]["harness"] == "claude-code"
    assert items[0]["tools"] == ["library-mcp"]
    assert items[0]["outcome"] == "partial"
    assert items[0]["submitted_by_agent"] is False
    assert items[0]["author"] is None


@pytest.mark.django_db
def test_list_traces_filters_by_submission(client: Client) -> None:
    library = Submission.objects.create(title="Renew my library card")
    park = Submission.objects.create(title="Book a park")
    RunTrace.objects.create(
        submission=library, model="m", harness="h", outcome=RunTrace.Outcome.SUCCESS
    )
    RunTrace.objects.create(
        submission=park, model="m", harness="h", outcome=RunTrace.Outcome.FAILED
    )
    response = client.get("/api/traces/", {"submission_id": library.pk})
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["submission_id"] == library.pk


@pytest.mark.django_db
def test_list_traces_paginates_with_limit_offset(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    for _ in range(3):
        RunTrace.objects.create(
            submission=submission, model="m", harness="h", outcome=RunTrace.Outcome.SUCCESS
        )
    page = client.get("/api/traces/?limit=2&offset=0").json()
    assert page["count"] == 3  # total, not the page size
    assert len(page["items"]) == 2
    assert len(client.get("/api/traces/?limit=2&offset=2").json()["items"]) == 1


# --- create ---------------------------------------------------------------


@pytest.mark.django_db
def test_create_requires_auth(client: Client) -> None:
    submission = Submission.objects.create(title="Book a park")
    response = client.post("/api/traces/", payload(submission), content_type="application/json")
    assert response.status_code == 401
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_human_creates_trace_attributed_to_self(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        payload(submission),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["submitted_by_agent"] is False
    assert body["author"] == "alice"
    assert body["submission_id"] == submission.pk
    assert body["outcome"] == "success"


@pytest.mark.django_db
def test_agent_with_scope_creates_agent_flagged_trace(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    raw = agent_key(human, name="runner", scopes=[SCOPE_TRACES_WRITE])
    submission = Submission.objects.create(title="Draft block-party permits")
    response = client.post(
        "/api/traces/",
        payload(submission),
        content_type="application/json",
        headers=bearer(raw),
    )
    assert response.status_code == 201
    body = response.json()
    # A trace reported by an agent is flagged and attributed to the agent's own
    # username (BRIEF: agent content is distinguishable, with a username).
    assert body["submitted_by_agent"] is True
    assert body["author"] == "alice-bot"


@pytest.mark.django_db
def test_agent_without_scope_is_forbidden(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    raw = agent_key(human, name="noscope", scopes=[])
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        payload(submission),
        content_type="application/json",
        headers=bearer(raw),
    )
    assert response.status_code == 403
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_create_unknown_submission_returns_404(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    response = client.post(
        "/api/traces/",
        {
            "submission_id": "NOTAREALID",
            "model": "m",
            "harness": "h",
            "outcome": "success",
            "transcript": [{"kind": "user", "content": "hi"}],
        },
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 404
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_create_rejects_unknown_outcome(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        payload(submission, outcome="mostly-fine"),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 422
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_create_ignores_client_asserted_agent_flag(client: Client) -> None:
    # A human cannot masquerade as an agent by setting the flag in the body.
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        payload(submission, submitted_by_agent=True),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    assert response.json()["submitted_by_agent"] is False


# --- transcript (ADR-0011) ------------------------------------------------


@pytest.mark.django_db
def test_create_persists_transcript(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Renew my library card")
    response = client.post(
        "/api/traces/",
        payload(submission, transcript=TRANSCRIPT),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    assert RunTrace.objects.get().transcript == TRANSCRIPT
    # The create response is the lean TraceOut — the transcript is not echoed.
    assert "transcript" not in response.json()


@pytest.mark.django_db
def test_create_derives_tools_from_transcript(client: Client) -> None:
    # `tools` is not accepted from the body — it is the distinct, sorted set of
    # tool_call names in the transcript. Any `tools` in the body is ignored.
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Renew my library card")
    transcript = [
        {"kind": "user", "content": "renew"},
        {"kind": "tool_call", "name": "library-mcp.lookup", "input": {}},
        {"kind": "tool_result", "output": "ok"},
        {"kind": "tool_call", "name": "mbta-mcp.plan", "input": {}},
        {"kind": "tool_call", "name": "library-mcp.lookup", "input": {}},  # duplicate
    ]
    response = client.post(
        "/api/traces/",
        payload(submission, transcript=transcript, tools=["should-be-ignored"]),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    assert response.json()["tools"] == ["library-mcp.lookup", "mbta-mcp.plan"]
    assert RunTrace.objects.get().tools == ["library-mcp.lookup", "mbta-mcp.plan"]


@pytest.mark.django_db
def test_create_with_no_tool_calls_derives_empty_tools(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        payload(submission, transcript=[{"kind": "assistant", "content": "done"}]),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    assert RunTrace.objects.get().tools == []


@pytest.mark.django_db
def test_create_rejects_missing_transcript(client: Client) -> None:
    # A trace must carry its evidence; a summary without steps is `422`.
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    body = payload(submission)
    del body["transcript"]
    response = client.post(
        "/api/traces/", body, content_type="application/json", headers=basic("alice", PASSWORD)
    )
    assert response.status_code == 422
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_create_rejects_empty_transcript(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        payload(submission, transcript=[]),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 422
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_list_omits_transcript(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    RunTrace.objects.create(
        submission=submission,
        model="m",
        harness="h",
        outcome=RunTrace.Outcome.SUCCESS,
        transcript=TRANSCRIPT,
    )
    body = client.get("/api/traces/").json()
    # The list stays lean; transcripts are served per-id (FR-2, FR-7).
    assert "transcript" not in body["items"][0]


@pytest.mark.django_db
def test_detail_endpoint_returns_transcript(client: Client) -> None:
    submission = Submission.objects.create(title="Renew my library card")
    trace = RunTrace.objects.create(
        submission=submission,
        model="claude-opus-4-8",
        harness="claude-code",
        outcome=RunTrace.Outcome.SUCCESS,
        transcript=TRANSCRIPT,
    )
    response = client.get(f"/api/traces/{trace.pk}")
    assert response.status_code == 200
    assert response.json()["transcript"] == TRANSCRIPT


@pytest.mark.django_db
def test_detail_endpoint_unknown_id_is_404(client: Client) -> None:
    assert client.get("/api/traces/NOTAREALID").status_code == 404


@pytest.mark.django_db
def test_create_rejects_unknown_step_kind(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        payload(submission, transcript=[{"kind": "mumble", "content": "hi"}]),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 422
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_create_rejects_step_missing_required_field(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        "/api/traces/",
        # a tool_call with no `name`
        payload(submission, transcript=[{"kind": "tool_call", "input": {}}]),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 422
    assert RunTrace.objects.count() == 0


@pytest.mark.django_db
def test_create_rejects_transcript_over_cap(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    huge = [{"kind": "user", "content": "x"}] * (MAX_TRANSCRIPT_STEPS + 1)
    response = client.post(
        "/api/traces/",
        payload(submission, transcript=huge),
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 422
    assert RunTrace.objects.count() == 0


# --- external_urls: links surfaced in a run, for the trace-detail breakout ----
#
# Pure transcript parsing (no DB): distinct http(s) URLs from `tool_call` inputs,
# `tool_result` outputs, and `assistant` text, deduped in first-seen order.


def test_external_urls_pulls_from_tool_calls_results_and_assistant() -> None:
    urls = RunTrace.external_urls(
        [
            {"kind": "user", "content": "check https://user.example should be ignored"},
            {"kind": "reasoning", "content": "https://reasoning.example ignored too"},
            {"kind": "assistant", "content": "See https://assistant.example for details"},
            {
                "kind": "tool_call",
                "name": "fetch",
                "input": {"url": "https://tool-call.example/page"},
            },
            {"kind": "tool_result", "output": "landed on https://tool-result.example ok"},
        ]
    )
    assert urls == [
        "https://assistant.example",
        "https://tool-call.example/page",
        "https://tool-result.example",
    ]
    # user prompts and private reasoning are not part of the breakout.
    assert not any("user.example" in u or "reasoning.example" in u for u in urls)


def test_external_urls_dedupes_preserving_first_seen_order() -> None:
    urls = RunTrace.external_urls(
        [
            {"kind": "assistant", "content": "https://b.example then https://a.example"},
            {"kind": "tool_result", "output": "again https://a.example and https://b.example"},
        ]
    )
    assert urls == ["https://b.example", "https://a.example"]


def test_external_urls_strips_trailing_punctuation_and_wrappers() -> None:
    urls = RunTrace.external_urls(
        [
            {"kind": "assistant", "content": "done (see https://mass.gov/renew). thanks"},
            {"kind": "assistant", "content": "link: https://boston.gov/library, or the map"},
        ]
    )
    assert urls == ["https://mass.gov/renew", "https://boston.gov/library"]


def test_external_urls_only_http_schemes() -> None:
    urls = RunTrace.external_urls(
        [
            {"kind": "tool_call", "name": "mail", "input": {"to": "mailto:clerk@boston.gov"}},
            {"kind": "tool_call", "name": "run", "input": {"cmd": "cat file:///etc/passwd"}},
            {"kind": "assistant", "content": "ok https://mass.gov and http://neu.edu"},
        ]
    )
    assert urls == ["https://mass.gov", "http://neu.edu"]


def test_external_urls_empty_when_none_present() -> None:
    assert RunTrace.external_urls([{"kind": "assistant", "content": "no links here"}]) == []
