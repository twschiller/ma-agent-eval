# Project semgrep rules

Custom static-analysis rules for this repo, run by the `semgrep` pre-commit hook
and the `semgrep` CI job (`uv run semgrep scan --config .semgrep --error`).

The plumbing is in place so rules can be added incrementally — drop a new
`*.yml` rule file in `rules/` and it's picked up automatically. See
<https://semgrep.dev/docs/writing-rules/overview> for the rule format, or copy
from the registry (<https://semgrep.dev/r>).

`rules/starter.yml` holds a couple of low-false-positive examples to demonstrate
the pattern. Delete or extend them as the codebase's real invariants emerge —
things worth catching here are project-specific patterns bandit/ruff don't cover
(e.g. "never call the vendor API client outside `services/`", "agent-authored
content must set `submitted_by_agent`").
