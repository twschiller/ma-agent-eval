---
status: accepted
date: 2026-07-11
---

# Search submissions with query-time Postgres full-text search

## Context and Problem Statement

`BRIEF.md` lists "unauthenticated principal can search submissions" as a primary
user story — the last one unbuilt. The submissions catalog is a public,
human-upvoted backlog of civic tasks; a visitor needs to find "renew my library
card" without knowing its exact title. This ADR decides the *matching mechanism*
for that search and how it is indexed. Pagination of the list endpoints is a
separate, non-significant change (Ninja's built-in `LimitOffset`) and not
relitigated here.

Postgres is the database in every environment (`config/settings/base.py`), so
there is no SQLite fallback to accommodate — the full-text search feature set is
available uniformly in dev, test, and prod.

## Considered Options

- **`icontains` substring match.** `filter(title__icontains=q)`. Trivial, but no
  stemming ("libraries" ≠ "library"), no ranking, no multi-word relevance — a
  naive `LIKE '%q%'` that also can't use an index.
- **Query-time Postgres FTS.** `SearchVector("title","description")` +
  `SearchRank`, computed per query, ordered by relevance. Real stemming and
  ranking, zero schema change, no index. Sequential scan per search.
- **Indexed FTS: `SearchVectorField` + `GinIndex`.** A maintained `tsvector`
  column (generated column or trigger) backed by a GIN index. Same semantics as
  query-time but O(log n); costs a migration and a vector-freshness strategy.

## Decision Outcome

Chosen option: "query-time Postgres FTS", because it gives correct search
semantics — stemming, multi-word relevance ranking — at the cost of one import
and no schema change, and the catalog's scale (hundreds to low-thousands of
public civic tasks, gated by human upvotes) makes the sequential-scan cost
irrelevant. `icontains` is rejected: it looks cheaper but ships worse search
(no stemming or ranking) that we would only have to replace.

The indexed `SearchVectorField` + `GinIndex` option is **deferred, not rejected**:
it is the correct next step *if and when* the submission volume or search latency
warrants an index, and it is a drop-in successor to this decision (same
`SearchVector`/`SearchRank` query, plus a maintained column and index). Building
it now would add a migration and a vector-freshness mechanism to guard against a
scale we do not have — premature.

User input reaches the search via `SearchQuery(q, search_type="websearch")`.
`websearch` parses arbitrary input (quotes, `OR`, `-term`) without raising on
malformed syntax, so the public, unauthenticated search box cannot 500 on a
hostile or sloppy query. Zero matches return an empty page, not an error.

### Consequences

- Good, because search ships with real relevance ranking and stemming for
  effectively no schema or infra cost.
- Good, because the endpoint stays a plain paginated list: `q` is an optional
  filter on the same queryset, so search and browse share one contract and one
  `LimitOffset` pagination path.
- Good, because `websearch` parsing means no user string can crash the endpoint.
- Bad, because each search is a sequential scan with a per-row `tsvector`
  computation — fine at current scale, degrades as submissions grow.
- Locks in: `django.contrib.postgres` in `INSTALLED_APPS`; search over
  `title` + `description` only; relevance (`-rank`) then recency (`-created_at`)
  ordering. Enforced by `maeval/submissions/tests/test_submissions.py`.

## More Information

- Supersedes / superseded by: none
- Spec: `docs/requirements/submissions.md`
- Files: `maeval/submissions/views.py`, `config/settings/base.py`
- Future work: indexed `SearchVectorField` + `GinIndex` when volume warrants —
  a drop-in successor, tracked here until it gets its own ADR.
- External: Postgres full-text search; Django `django.contrib.postgres.search`
  (`SearchVector`, `SearchQuery`, `SearchRank`); `websearch_to_tsquery`
