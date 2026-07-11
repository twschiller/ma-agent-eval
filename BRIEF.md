
Context
---
- MA AI Agents for All Working Group
- [RFC: Public Infrastructure Framework for Private Agents: An AI Agent for Every Massachusetts Resident](https://docs.google.com/document/d/1CPTeGieguR_Jbq69YnWqMMM4m9tm0POekTbUbQn82ag/edit)
- Working Group 2: Working Group 2 — Civic Services Interface: What services should be exposed through MCP in Phase 2 (submission, not just read)? What are the security and liability requirements for each service category? How do we handle non-determinism and cascading failures when agents interact with deterministic government systems?
- Government infrastructure at different levels of maturity: in person, mail-in form, online form, API, MCP

Key Objectives
---
- Brainstorm and prioritize use cases that humans would like AI agents to perform
- Identify capabilities/maturity of MA and Boston government systems for use case
- Identify capability of AI agents to perform use case (LLMs, harness, etc.)

Primary User Stories
---
- Human or AI Agent can sign up for an account using username and password
- Authenticated principal can create named API key(s) for their agents and choose permission scopes
- Authenticated principal can submit queries, tasks, jobs to be done that they'd like an agent to be able to do
- Unauthenticated principal can view submissions and upvote count
- Unauthenticated principal can upvote submissions
- Authenticated principal can submit AI Agent run trace for a given query/task/job to be done:
  - Identifies which model, harness, and tools were used
  - Identifies judgment if the run was successful, partially successful, or failed
- Unauthenticated principal can view AI Agent run traces

Requirements
---
- OpenAPI schema for all endpoints that should be accessible to AI agents
- Content submitted by agent is identified as being submitted by an AI agent (with associated username)
- Content Moderation: admin can delete all content submitted associated with a human account (and their AI agents)

Examples
---
- Can you renew my library card?
- Can you book a park on August 8th for a birthday party within 20 minutes of my house?
- Are there any MBTA alerts that will affect my commute today?
- Can you draft the permits I need for a block party?