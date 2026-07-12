"""Tests for the run-traces API: public list (with filter) and scoped create."""

import base64

import pytest
from django.test import Client

from maeval.accounts.models import SCOPE_TRACES_WRITE, ApiKey, User
from maeval.submissions.models import Submission
from maeval.traces.models import RunTrace

PASSWORD = "corr3ct-horse-b4ttery"


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
        "tools": ["mbta-mcp"],
        "outcome": "success",
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
        {"submission_id": "NOTAREALID", "model": "m", "harness": "h", "outcome": "success"},
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
