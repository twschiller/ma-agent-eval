"""HTTP layer for accounts: signup, agent creation, API-key issuance, /me.

Depends on schemas, auth, and models. `submitted_by_agent`-style attribution is
never taken from a request body here — it is derived from the authenticated
principal by the auth layer.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Status

from maeval.accounts.auth import ANY_PRINCIPAL, HumanBasicAuth
from maeval.accounts.models import SCOPES, ApiKey, User
from maeval.accounts.schemas import (
    AgentIn,
    ApiKeyCreatedOut,
    ApiKeyIn,
    SignupIn,
    UserOut,
)

router = Router(tags=["accounts"])


@router.post("/signup", response={201: UserOut}, auth=None)
def signup(request, payload: SignupIn) -> Status[User]:  # noqa: ARG001
    """Create a human principal from a username + password."""
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(409, "username already taken")
    try:
        validate_password(payload.password)
    except ValidationError as exc:
        raise HttpError(422, "; ".join(exc.messages)) from exc
    user = User.objects.create_user(
        username=payload.username, password=payload.password, email=payload.email
    )
    return Status(201, user)


@router.get("/me", response=UserOut, auth=ANY_PRINCIPAL)
def me(request) -> User:
    """Return the authenticated principal — human or agent."""
    return request.auth


@router.post("/agents", response={201: UserOut}, auth=HumanBasicAuth())
def create_agent(request, payload: AgentIn) -> Status[User]:
    """Register an AI agent owned by the authenticated human principal."""
    human: User = request.auth
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(409, "username already taken")
    try:
        agent = User.create_agent(username=payload.username, parent=human)
    except ValidationError as exc:
        raise HttpError(422, "; ".join(exc.messages)) from exc
    return Status(201, agent)


@router.post("/agents/{agent_id}/keys", response={201: ApiKeyCreatedOut}, auth=HumanBasicAuth())
def issue_key(request, agent_id: str, payload: ApiKeyIn) -> Status[ApiKey]:
    """Mint an API key for one of the caller's agents. Raw key returned once."""
    human: User = request.auth
    try:
        agent = User.objects.get(pk=agent_id, parent=human, is_agent=True)
    except User.DoesNotExist as exc:
        raise HttpError(404, "no such agent for this principal") from exc
    unknown = set(payload.scopes) - SCOPES
    if unknown:
        raise HttpError(422, f"unknown scopes: {', '.join(sorted(unknown))}")
    key, raw = ApiKey.issue(agent=agent, name=payload.name, scopes=payload.scopes)
    # Attach the one-time raw token onto the response object.
    key.api_key = raw  # type: ignore[attr-defined]  # transient, not a model field
    return Status(201, key)
