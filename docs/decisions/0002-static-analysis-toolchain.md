---
status: accepted
date: 2026-07-11
---

# Wire the full static-analysis toolchain up front

## Context and Problem Statement

This is an agent-facing public API handling authN/authZ, API keys, user-submitted
content, and moderation — a surface where a class of bug becomes a class of
incident. Adding lint/security tooling piecemeal later means retrofitting a clean
bill of health across a grown codebase each time, and each addition lands as a
noisy, hard-to-review PR. The question: which static-analysis tools do we commit
to, and when?

## Considered Options

- Wire every tool (ruff, pyright, bandit, semgrep, tach, gitleaks, zizmor,
  actionlint, hadolint, shellcheck) into pre-commit + CI at bootstrap, even with
  empty/starter rule sets.
- Add tools reactively as needs surface.
- Rely on GitHub-native scanning (CodeQL/Dependabot) only.

## Decision Outcome

Chosen option: "wire every tool up front", because on a zero-line codebase every
tool passes trivially, so the cost is one bootstrap PR instead of N retrofit PRs,
and the gate ratchets: it can only stay green as code is added. semgrep is
included with a starter rule set in `.semgrep/rules/` even though few
project-specific rules exist yet — the plumbing (pre-commit hook, CI job,
`make semgrep`) is the expensive part to add later, not the rules.

### Consequences

- Good, because every new tool is a rule/config change, never a
  toolchain-plumbing change — additions are small and reviewable.
- Good, because the security-relevant tools (bandit, semgrep, gitleaks) are
  enforcing from commit #1, before the auth/API-key code exists.
- Bad, because some tools (semgrep, zizmor, hadolint) start with thin or generic
  rule sets and provide little signal until tuned — accepted as cheap.
- Locks in: static-analysis tools are enforced via pre-commit + CI as separate
  status checks; new rules are added to existing tools, not new tools bolted on
  ad hoc. Enforced by `.pre-commit-config.yaml` and `.github/workflows/ci.yml`.

## More Information

- Files: `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.semgrep/`,
  `tach.toml`, `pyproject.toml`
