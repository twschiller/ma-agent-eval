"""Moderation is Django-admin deletion of a principal plus DB cascade (ADR-0004).

There is no moderation endpoint; these tests assert the model-level invariant the
admin relies on: deleting a human principal removes the human, its agents, their
API keys, and all content (submissions, traces, votes) authored by any of them —
the BRIEF's "delete all content associated with a human account and their AI
agents". They exercise the ORM directly because that is exactly what the admin
delete does.
"""

import pytest

from maeval.accounts.models import SCOPE_SUBMISSIONS_WRITE, SCOPE_TRACES_WRITE, ApiKey, User
from maeval.submissions.models import Submission, Vote
from maeval.traces.models import RunTrace

PASSWORD = "corr3ct-horse-b4ttery"


def _principal_with_content(username: str) -> User:
    """Build a human, an agent it owns, an API key, and content from both."""
    human = User.objects.create_user(username=username, password=PASSWORD)
    agent = User.create_agent(username=f"{username}-bot", parent=human)
    ApiKey.issue(agent=agent, name="k", scopes=[SCOPE_SUBMISSIONS_WRITE, SCOPE_TRACES_WRITE])

    human_sub = Submission.objects.create(title=f"{username} task", author=human)
    agent_sub = Submission.objects.create(
        title=f"{username} agent task", author=agent, submitted_by_agent=True
    )
    RunTrace.objects.create(
        submission=human_sub, author=agent, model="m", harness="h", outcome="success"
    )
    Vote.objects.create(submission=agent_sub, voter=human)
    return human


@pytest.mark.django_db
def test_deleting_human_cascades_to_agents_and_keys() -> None:
    human = _principal_with_content("alice")

    human.delete()

    # The human and its agent are gone; so is the agent's key.
    assert not User.objects.filter(username="alice").exists()
    assert not User.objects.filter(username="alice-bot").exists()
    assert ApiKey.objects.count() == 0


@pytest.mark.django_db
def test_deleting_human_deletes_all_its_content() -> None:
    human = _principal_with_content("alice")

    human.delete()

    # BRIEF: all content by the human AND its agents is removed, not tombstoned.
    assert Submission.objects.count() == 0
    assert RunTrace.objects.count() == 0
    assert Vote.objects.count() == 0


@pytest.mark.django_db
def test_moderation_is_scoped_to_one_principal() -> None:
    doomed = _principal_with_content("alice")
    _principal_with_content("bob")

    doomed.delete()

    # Only alice's world is gone; bob (human + agent + content) is untouched.
    assert User.objects.filter(username="bob").exists()
    assert User.objects.filter(username="bob-bot").exists()
    assert Submission.objects.count() == 2
    assert RunTrace.objects.count() == 1
    assert Vote.objects.count() == 1
