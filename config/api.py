"""Django Ninja API composition root.

Mounts each app's router and exposes the OpenAPI schema that AI-agent clients
consume. `tools/export_openapi.py` serializes `api.get_openapi_schema()` for the
spectral lint hook.
"""

from ninja import NinjaAPI, Schema

from maeval.accounts.views import router as accounts_router
from maeval.submissions.views import router as submissions_router
from maeval.traces.views import router as traces_router

api = NinjaAPI(
    title="MA Agent Eval API",
    version="0.1.0",
    description="Catalog of agent-performable civic tasks, upvotes, and run traces.",
)


class Health(Schema):
    status: str


@api.get("/healthz", response=Health, tags=["ops"], auth=None)
def healthz(request) -> Health:  # noqa: ARG001  (Ninja passes the request)
    """Liveness probe used by the Fly.io health check."""
    return Health(status="ok")


api.add_router("/accounts", accounts_router)
api.add_router("/submissions", submissions_router)
api.add_router("/traces", traces_router)
