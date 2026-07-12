"""Forms for the web UI. Depends on models only (see tach.toml).

These back the browser write paths (login, signup, create submission, and — for
a human managing their agents — registering an agent and issuing it an API key,
ADR-0009). A human self-serves key management here; agents themselves still act
only through the API.
"""

import hmac
from typing import ClassVar

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from maeval.accounts.models import SCOPES, User
from maeval.submissions.models import Submission

# Human-readable names for the API-key scopes. ``SCOPES`` (the model) stays the
# source of truth for *which* scopes exist; this only labels them for the browser
# form, so an unknown scope here would surface as a missing key, not a silent typo.
SCOPE_LABELS: dict[str, str] = {
    "submissions:write": "Submit tasks",
    "submissions:vote": "Upvote tasks",
    "traces:write": "Record run traces",
}


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


class AgentForm(FieldStyleMixin, forms.ModelForm):
    """Register an AI agent under the logged-in human (ADR-0009).

    Only the username is collected — ``is_agent`` and ``parent`` are set from the
    session principal in the view via ``User.create_agent``, never posted, the
    same attribution rule the API's ``create_agent`` enforces. A ``ModelForm`` on
    ``User`` reuses the model's username validator and uniqueness check.
    """

    class Meta:
        model = User
        fields = ("username",)


class ApiKeyForm(FieldStyleMixin, forms.Form):
    """Issue a scoped API key for one of the caller's agents (ADR-0009).

    Scopes are a multi-select over the known set, so an unknown scope can't be
    submitted (the API rejects one with 422; here the field forbids it). Expiry
    is optional and must be in the future — mirrors ``issue_key``.
    """

    name = forms.CharField(
        max_length=100,
        help_text="A label to recognize this key later, e.g. “laptop” or “CI runner”.",
    )
    scopes = forms.MultipleChoiceField(
        choices=[(scope, SCOPE_LABELS[scope]) for scope in sorted(SCOPES)],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="What this key may do. Grant the least the agent needs.",
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Optional. The key stops working after this date; blank means it never expires.",
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        # The style mixin tags every widget with `field-input` (sized for text
        # boxes); strip it from the checkbox list so the scopes render as plain
        # checkboxes, not full-width inputs.
        self.fields["scopes"].widget.attrs.pop("class", None)

    def clean_expires_at(self) -> object:
        expires_at = self.cleaned_data.get("expires_at")
        if expires_at is None:
            return None
        # A `type="date"` value parses to a naive midnight; anchor it to the
        # active timezone before comparing so USE_TZ storage stays consistent.
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at)
        if expires_at <= timezone.now():
            raise forms.ValidationError("Pick a date in the future.")
        return expires_at


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
