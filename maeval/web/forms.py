"""Forms for the web UI. Depends on models only (see tach.toml).

These back the browser write paths (login, signup, create submission). Agent-only
concerns — API keys, scopes — never appear here; agents act through the API.
"""

from typing import ClassVar

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from maeval.accounts.models import User
from maeval.submissions.models import Submission


class FieldStyleMixin:
    """Tag every visible field widget with the design system's ``field-input``
    class (see ``maeval.css``), so browser forms render with the project's own
    input styling rather than Bootstrap defaults.
    """

    fields: dict  # provided by Form/ModelForm

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[misc]  # cooperative mixin
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} field-input".strip()


class LoginForm(FieldStyleMixin, AuthenticationForm):
    """Session login for a human principal (username + password)."""


class SignupForm(FieldStyleMixin, UserCreationForm):
    """Register a human principal (username + password).

    A web signup is always a human: agents carry unusable passwords and never
    session-log-in, so the created user keeps the model defaults
    (``is_agent=False``, ``parent=None``). Password strength is enforced by
    ``AUTH_PASSWORD_VALIDATORS`` via ``UserCreationForm``, matching the API's
    ``/accounts/signup``.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class SubmissionForm(FieldStyleMixin, forms.ModelForm):
    """Create a submission from the browser. ``author`` and
    ``submitted_by_agent`` are set from the logged-in principal in the view,
    never from the posted data — the same attribution rule as the API."""

    class Meta:
        model = Submission
        fields = ("title", "description")
        widgets: ClassVar[dict] = {
            "title": forms.TextInput(attrs={"placeholder": "Renew my library card"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
