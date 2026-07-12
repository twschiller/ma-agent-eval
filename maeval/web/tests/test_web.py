"""Tests for the server-rendered web UI (ADR-0006).

Covers the public read surface, htmx search/upvote fragments, and the
session-auth write paths. The API surface has its own tests; here we assert the
HTML layer and that attribution/vote semantics match via the shared helpers.
"""

from urllib.parse import urlencode

import pytest
from django.test import Client
from django.urls import reverse

from maeval.accounts.models import User
from maeval.submissions.models import Submission, Vote
from maeval.traces.models import RunTrace

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


@pytest.mark.django_db
def test_agent_content_is_badged(client: Client) -> None:
    submission = Submission.objects.create(title="Agent task", submitted_by_agent=True)
    response = client.get(reverse("web:submission_detail", args=[submission.pk]))
    assert b"agent" in response.content


@pytest.mark.django_db
def test_home_links_to_llms_txt(client: Client) -> None:
    response = client.get(reverse("web:home"))
    assert reverse("web:llms_txt") in response.content.decode()


@pytest.mark.django_db
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
def test_login_flow(client: Client, human: User) -> None:
    response = client.post(reverse("web:login"), {"username": "alice", "password": PASSWORD})
    assert response.status_code == 302
    assert "_auth_user_id" in client.session


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
