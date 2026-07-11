"""Tests for identity: signup, agent creation, API keys, and auth."""

import base64

import pytest
from django.db import IntegrityError
from django.test import Client
from django.utils import timezone

from maeval.accounts.models import ApiKey, User

PASSWORD = "corr3ct-horse-b4ttery"


@pytest.fixture
def client() -> Client:
    return Client()


def basic(username: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"authorization": f"Basic {raw}"}


def bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


# --- signup ---------------------------------------------------------------


@pytest.mark.django_db
def test_signup_creates_human(client: Client) -> None:
    response = client.post(
        "/api/accounts/signup",
        {"username": "alice", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["is_agent"] is False
    assert body["parent_id"] is None
    assert User.objects.get(username="alice").check_password(PASSWORD)


@pytest.mark.django_db
def test_signup_rejects_duplicate_username(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    response = client.post(
        "/api/accounts/signup",
        {"username": "alice", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_signup_rejects_weak_password(client: Client) -> None:
    response = client.post(
        "/api/accounts/signup",
        {"username": "alice", "password": "123"},
        content_type="application/json",
    )
    assert response.status_code == 422


# --- /me ------------------------------------------------------------------


@pytest.mark.django_db
def test_me_requires_auth(client: Client) -> None:
    assert client.get("/api/accounts/me").status_code == 401


@pytest.mark.django_db
def test_me_returns_human_over_basic(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    response = client.get("/api/accounts/me", headers=basic("alice", PASSWORD))
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


@pytest.mark.django_db
def test_me_rejects_agent_over_basic(client: Client) -> None:
    # Agents have no usable password; they cannot use the human Basic scheme.
    human = User.objects.create_user(username="alice", password=PASSWORD)
    User.create_agent(username="alice-bot", parent=human)
    assert client.get("/api/accounts/me", headers=basic("alice-bot", PASSWORD)).status_code == 401


# --- agent creation + attribution ----------------------------------------


@pytest.mark.django_db
def test_create_agent_links_to_parent(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    response = client.post(
        "/api/accounts/agents",
        {"username": "alice-bot"},
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_agent"] is True
    assert body["parent_id"] == human.pk
    agent = User.objects.get(username="alice-bot")
    assert agent.principal == human


@pytest.mark.django_db
def test_create_agent_requires_human_auth(client: Client) -> None:
    response = client.post(
        "/api/accounts/agents",
        {"username": "orphan-bot"},
        content_type="application/json",
    )
    assert response.status_code == 401


# --- API keys -------------------------------------------------------------


@pytest.mark.django_db
def test_issue_key_returns_raw_once_and_stores_only_hash(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    agent = User.create_agent(username="alice-bot", parent=human)
    response = client.post(
        f"/api/accounts/agents/{agent.pk}/keys",
        {"name": "laptop", "scopes": ["submissions:write"]},
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 201
    body = response.json()
    raw = body["api_key"]
    assert raw.startswith("mae_")
    key = ApiKey.objects.get(pk=body["id"])
    # The secret is never persisted; only prefix + hash are.
    assert raw.split("_")[2] not in key.hashed_secret
    assert ApiKey.resolve(raw) == key


@pytest.mark.django_db
def test_agent_authenticates_with_key(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    agent = User.create_agent(username="alice-bot", parent=human)
    _key, raw = ApiKey.issue(agent=agent, name="ci", scopes=[])
    response = client.get("/api/accounts/me", headers=bearer(raw))
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice-bot"
    assert body["is_agent"] is True
    assert body["parent_id"] == human.pk


@pytest.mark.django_db
def test_issue_key_rejects_foreign_agent(client: Client) -> None:
    alice = User.objects.create_user(username="alice", password=PASSWORD)
    bob = User.objects.create_user(username="bob", password=PASSWORD)
    bob_bot = User.create_agent(username="bob-bot", parent=bob)
    response = client.post(
        f"/api/accounts/agents/{bob_bot.pk}/keys",
        {"name": "steal", "scopes": []},
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 404
    assert alice  # alice is a valid human; the agent just isn't hers


@pytest.mark.django_db
def test_issue_key_rejects_unknown_scope(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    agent = User.create_agent(username="alice-bot", parent=human)
    response = client.post(
        f"/api/accounts/agents/{agent.pk}/keys",
        {"name": "bad", "scopes": ["root:everything"]},
        content_type="application/json",
        headers=basic("alice", PASSWORD),
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_revoked_key_does_not_resolve(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    agent = User.create_agent(username="alice-bot", parent=human)
    key, raw = ApiKey.issue(agent=agent, name="ci", scopes=[])
    key.revoked_at = timezone.now()
    key.save(update_fields=["revoked_at"])
    assert ApiKey.resolve(raw) is None


# --- model invariants -----------------------------------------------------


@pytest.mark.django_db
def test_human_cannot_have_parent(client: Client) -> None:
    human = User.objects.create_user(username="alice", password=PASSWORD)
    with pytest.raises(IntegrityError):
        User.objects.create(username="bad", is_agent=False, parent=human)


@pytest.mark.django_db
def test_agent_must_have_parent(client: Client) -> None:
    with pytest.raises(IntegrityError):
        User.objects.create(username="bad-bot", is_agent=True, parent=None)
