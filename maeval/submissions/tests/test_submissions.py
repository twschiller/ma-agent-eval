"""Smoke tests for the submissions API and the health check."""

import pytest
from django.test import Client

from maeval.submissions.models import Submission


@pytest.fixture
def client() -> Client:
    return Client()


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
