#!/usr/bin/env python
"""Serialize the Django Ninja OpenAPI schema to `openapi.json` at the repo root.

Run by the `spectral-openapi` pre-commit hook and `make schema`. Keeping the
schema on disk lets spectral lint it and lets agent clients diff API changes in
review. Uses the test settings so no database or secrets are required.
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django  # noqa: E402

django.setup()

from config.api import api  # noqa: E402

OUTPUT = REPO_ROOT / "openapi.json"


def main() -> None:
    schema = api.get_openapi_schema()
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    sys.stdout.write(f"Wrote {OUTPUT}\n")


if __name__ == "__main__":
    main()
