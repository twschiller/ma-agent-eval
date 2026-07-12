"""URLconf for the web UI, included at the site root by ``config/urls.py``.

The "no per-app urls.py" convention (AGENTS.md) applies to the API apps, whose
Ninja routers mount centrally in ``config/api.py``. The web app has no router,
so it owns a namespaced URLconf here (see ADR-0006). Session login/logout reuse
Django's built-in auth views with our templates.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from maeval.web import views
from maeval.web.forms import LoginForm

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("llms.txt", views.llms_txt, name="llms_txt"),
    path("submissions/", views.submission_list, name="submission_list"),
    # "new" is declared before the "<submission_id>" catch to keep it a page,
    # not a submission lookup.
    path("submissions/new/", views.submission_create, name="submission_create"),
    path("submissions/<str:submission_id>/", views.submission_detail, name="submission_detail"),
    path(
        "submissions/<str:submission_id>/upvote/",
        views.submission_upvote,
        name="submission_upvote",
    ),
    path("traces/", views.trace_list, name="trace_list"),
    # Agent + API-key management (ADR-0009). "new" precedes "<agent_id>" so it
    # stays a page, not an agent lookup — same ordering rule as submissions.
    path("agents/", views.agent_list, name="agent_list"),
    path("agents/new/", views.agent_create, name="agent_create"),
    path("agents/<str:agent_id>/", views.agent_detail, name="agent_detail"),
    path("agents/<str:agent_id>/keys/new/", views.key_create, name="key_create"),
    path("keys/<str:key_id>/revoke/", views.key_revoke, name="key_revoke"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="web/login.html", authentication_form=LoginForm),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.signup, name="signup"),
]
