"""Forms for the web UI. Depends on models only (see tach.toml).

These back the browser write paths (login, signup, create submission). Agent-only
concerns — API keys, scopes — never appear here; agents act through the API.
"""

import hmac
from typing import ClassVar

from django import forms
from django.conf import settings
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

    When ``SIGNUP_INVITE_CODE`` is set the form grows a required ``invite_code``
    field gating registration (invite-only trial, ADR-0008); when it is empty the
    field is absent and signup is open.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        if settings.SIGNUP_INVITE_CODE:
            # Added after the mixin has tagged the base fields, so carry the
            # design-system class on the widget ourselves.
            self.fields["invite_code"] = forms.CharField(
                label="Invite code",
                help_text="This trial is invite-only. Enter the code you were given.",
                widget=forms.TextInput(attrs={"class": "field-input", "autocomplete": "off"}),
            )

    def clean_invite_code(self) -> str:
        # Only reached when the field exists (i.e. a code is configured).
        expected = settings.SIGNUP_INVITE_CODE
        provided = self.cleaned_data.get("invite_code", "")
        # Constant-time compare so response timing can't leak the code.
        if not hmac.compare_digest(provided, expected):
            raise forms.ValidationError("That invite code isn't valid.")
        return provided


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
