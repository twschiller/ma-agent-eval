# Architecture Decision Records

MADR-minimal decision records. Append-only: supersede, never rewrite. One file
per decision, `NNNN-slug.md`, four-digit zero-padded so they sort lexically and
cite as `ADR-0007`. Use `adr-template.md` for new records.

| ADR                                           | Title                                              | Status   |
| --------------------------------------------- | -------------------------------------------------- | -------- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions in ADRs              | accepted |
| [0002](0002-static-analysis-toolchain.md)     | Wire the full static-analysis toolchain up front   | accepted |
| [0003](0003-identity-and-api-keys.md)         | Model AI agents as users linked to a human parent  | accepted |
| [0004](0004-content-moderation.md)            | Moderate by deleting the principal in Django admin | accepted |
| [0005](0005-full-text-search.md)              | Search submissions with query-time Postgres FTS    | accepted |
| [0006](0006-server-rendered-web-ui.md)        | Server-render the human web UI (templates + htmx)  | accepted |
