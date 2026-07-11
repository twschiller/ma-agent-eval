"""Tests for the submissions API: public list, create, and upvote."""

import base64

import pytest
from django.test import Client

from maeval.accounts.models import (
    SCOPE_SUBMISSIONS_VOTE,
    SCOPE_SUBMISSIONS_WRITE,
    ApiKey,
    User,
)
from maeval.submissions.models import Submission, Vote

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


# --- health + public list -------------------------------------------------


def test_healthz(client: Client) -> None:
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_list_submissions_empty(client: Client) -> None:
    response = client.get("/api/submissions/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_list_submissions_returns_created(client: Client) -> None:
    Submission.objects.create(title="Renew my library card")
    response = client.get("/api/submissions/")
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Renew my library card"
    assert body[0]["submitted_by_agent"] is False
    assert body[0]["author"] is None


# --- create ---------------------------------------------------------------


@pytest.mark.django_db
def test_create_requires_auth(client: Client) -> None:
    response = client.post(
        "/api/submissions/",
        {"title": "Book a park"},
        content_type="application/json",
    )
    assert response.status_code == 401
    assert Submission.objects.count() == 0


@pytest.mark.django_db
def test_human_creates_submission_attributed_to_self(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    response = client.post(
        "/api/submissions/",
        {"title": "Book a park", "description": "for a birthday"},
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["submitted_by_agent"] is False
    assert body["author"] == "alice"
    assert body["upvote_count"] == 0


@pytest.mark.django_db
def test_agent_with_scope_creates_agent_flagged_submission(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    raw = agent_key(human, name="writer", scopes=[SCOPE_SUBMISSIONS_WRITE])
    response = client.post(
        "/api/submissions/",
        {"title": "Draft block-party permits"},
        content_type="application/json",
        headers=bearer(raw),
    )
    assert response.status_code == 201
    body = response.json()
    # Content authored by an agent is flagged and attributed to the agent's
    # own username (BRIEF: agent content is distinguishable, with a username).
    assert body["submitted_by_agent"] is True
    assert body["author"] == "alice-bot"


@pytest.mark.django_db
def test_agent_without_scope_is_forbidden(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    raw = agent_key(human, name="reader", scopes=[])
    response = client.post(
        "/api/submissions/",
        {"title": "Nope"},
        content_type="application/json",
        headers=bearer(raw),
    )
    assert response.status_code == 403
    assert Submission.objects.count() == 0


@pytest.mark.django_db
def test_create_ignores_client_asserted_agent_flag(client: Client) -> None:
    # A human cannot masquerade as an agent by setting the flag in the body.
    User.objects.create_user(username="alice", password=PASSWORD)
    response = client.post(
        "/api/submissions/",
        {"title": "Book a park", "submitted_by_agent": True},
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    assert response.json()["submitted_by_agent"] is False


# --- upvote ---------------------------------------------------------------


@pytest.mark.django_db
def test_upvote_requires_auth(client: Client) -> None:
    submission = Submission.objects.create(title="Book a park")
    response = client.post(f"/api/submissions/{submission.pk}/upvote")
    assert response.status_code == 401


@pytest.mark.django_db
def test_upvote_missing_submission_returns_404(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    response = client.post("/api/submissions/NOTAREALID/upvote", headers=basic("alice", PASSWORD))
    assert response.status_code == 404


@pytest.mark.django_db
def test_human_upvote_increments_count(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = client.post(
        f"/api/submissions/{submission.pk}/upvote", headers=basic("alice", PASSWORD)
    )
    assert response.status_code == 200
    assert response.json()["upvote_count"] == 1
    assert Vote.objects.count() == 1


@pytest.mark.django_db
def test_upvote_is_idempotent_per_principal(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    response = None
    for _ in range(3):
        response = client.post(
            f"/api/submissions/{submission.pk}/upvote", headers=basic("alice", PASSWORD)
        )
        assert response.status_code == 200
    assert response is not None
    assert response.json()["upvote_count"] == 1
    assert Vote.objects.count() == 1


@pytest.mark.django_db
def test_agent_vote_counts_for_its_human_principal(client: Client) -> None:
    # A human and its agent together upvote a submission at most once.
    human = User.objects.create_user(username="alice", password=PASSWORD)
    raw = agent_key(human, name="voter", scopes=[SCOPE_SUBMISSIONS_VOTE])
    submission = Submission.objects.create(title="Book a park")
    assert (
        client.post(
            f"/api/submissions/{submission.pk}/upvote", headers=basic("alice", PASSWORD)
        ).status_code
        == 200
    )
    response = client.post(f"/api/submissions/{submission.pk}/upvote", headers=bearer(raw))
    assert response.status_code == 200
    assert response.json()["upvote_count"] == 1


@pytest.mark.django_db
def test_distinct_principals_accumulate_votes(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    User.objects.create_user(username="bob", password=PASSWORD)
    submission = Submission.objects.create(title="Book a park")
    client.post(f"/api/submissions/{submission.pk}/upvote", headers=basic("alice", PASSWORD))
    response = client.post(
        f"/api/submissions/{submission.pk}/upvote", headers=basic("bob", PASSWORD)
    )
    assert response.json()["upvote_count"] == 2


@pytest.mark.django_db
def test_agent_vote_without_scope_is_forbidden(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    raw = agent_key(human, name="noscope", scopes=[])
    submission = Submission.objects.create(title="Book a park")
    response = client.post(f"/api/submissions/{submission.pk}/upvote", headers=bearer(raw))
    assert response.status_code == 403
    assert Vote.objects.count() == 0
