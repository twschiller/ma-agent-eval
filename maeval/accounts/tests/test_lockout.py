"""Brute-force lockout (django-axes) on the authentication paths.

Axes is disabled for the rest of the suite (see `config.settings.test`) so
unrelated auth cases can't lock each other out; these tests re-enable it and
reset its state per test so each starts from a clean slate.
"""

import base64

import pytest
from axes.utils import reset
from django.test import Client, override_settings
from django.urls import reverse

from maeval.accounts.models import User

PASSWORD = "corr3ct-horse-b4ttery"
FAILURE_LIMIT = 3


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture(autouse=True)
def _reset_axes() -> None:
    # Axes writes attempts to the DB; the transaction rollback clears them, but
    # reset() also drops any cached lock so tests never see each other's state.
    reset()


def basic(username: str, password: str) -> dict[str, str]:
    raw = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"authorization": f"Basic {raw}"}


@pytest.mark.django_db
@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=FAILURE_LIMIT)
def test_web_login_locks_out_after_repeated_failures(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    url = reverse("web:login")
    for _ in range(FAILURE_LIMIT):
        client.post(url, {"username": "alice", "password": "wrong"})
    # Even the correct password is now refused: the (username, IP) pair is locked.
    response = client.post(url, {"username": "alice", "password": PASSWORD})
    assert response.status_code == 429
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=FAILURE_LIMIT)
def test_api_basic_auth_locks_out_after_repeated_failures(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    for _ in range(FAILURE_LIMIT):
        client.get("/api/accounts/me", headers=basic("alice", "wrong"))
    # Locked out: even valid credentials no longer authenticate.
    response = client.get("/api/accounts/me", headers=basic("alice", PASSWORD))
    assert response.status_code in (401, 429)


@pytest.mark.django_db
@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=FAILURE_LIMIT)
def test_login_below_threshold_still_succeeds(client: Client) -> None:
    User.objects.create_user(username="alice", password=PASSWORD)
    url = reverse("web:login")
    for _ in range(FAILURE_LIMIT - 1):
        client.post(url, {"username": "alice", "password": "wrong"})
    # A correct login before the limit both succeeds and (AXES_RESET_ON_SUCCESS)
    # clears the failure tally.
    response = client.post(url, {"username": "alice", "password": PASSWORD})
    assert response.status_code == 302
    assert "_auth_user_id" in client.session
