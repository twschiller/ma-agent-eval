"""Ninja I/O schemas for the submissions app. Depends only on models."""

from ninja import Schema


class SubmissionOut(Schema):
    id: str
    title: str
    description: str
    submitted_by_agent: bool
    upvote_count: int
