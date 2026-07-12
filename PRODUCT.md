# Product

## Register

product

## Platform

web

## Users

The primary audience is the **MA AI Agents for All working group** — civic
technologists, policy people, and government-adjacent contributors who curate
and prioritize what agents should be able to do against Massachusetts and Boston
civic services. Their context is deliberative: they come to compare demand
signals, weigh feasibility, and decide where effort is best spent. Two secondary
principals interact through the same surface — everyday residents who submit and
upvote tasks-to-be-done, and agent builders/researchers who contribute run
traces (model, harness, tools, outcome). The interface must read equally well to
a working-group member scanning for priorities and to a member of the public
suggesting a task, but the working group is who the design is tuned for.

## Product Purpose

A public catalog and eval harness for agent-performable civic tasks. Humans and
agents submit tasks-to-be-done ("renew my library card"), the public upvotes
them, and agents submit run traces showing what today's models and harnesses can
actually accomplish. Success is when the working group can look at the interface
and immediately see the **high bang-for-buck opportunities**: tasks with high
public demand that are also low-effort to enable — where a small change to a
civic interface unlocks disproportionate value. The product exists to turn
diffuse public demand and scattered agent evidence into a legible priority map.

## Positioning

The one place where public demand for civic agent tasks meets real evidence of
agent capability — so the highest-value, lowest-effort improvements to
Massachusetts civic interfaces become obvious rather than argued.

## Brand Personality

Civic and credible. Government-adjacent trust without the bureaucratic weight:
sober, clear, and institutional in the register of GOV.UK or the US Web Design
System, but never stuffy or cluttered. The voice is plain-language and
declarative — it states what a task is and what an agent did, and lets the
evidence carry the argument. It should feel like public infrastructure someone
takes seriously, not a product being sold.

## Anti-references

- **Generic Bootstrap default** — the current unstyled look (stock dark navbar,
  default cards, `display-6` hero). This needs a real, considered identity.
- **The generic Claude/AI-generated app look** — reflexive card grids, tiny
  tracked-uppercase eyebrows, hero-metric templates, gradient accents.
- **Flashy AI/SaaS startup** — gradient-drenched heroes, glassmorphism, hype
  copy. Wrong tone for civic public infrastructure.
- **Dated government bureaucracy** — cluttered, form-heavy, 2005 municipal-portal
  density. Credible is the goal, not archaic.
- **Playful / consumer-app** — bright, over-rounded, emoji-heavy, gamified.

## Design Principles

Signal over decoration — the demand-versus-effort read is the actual product;
every screen should make that judgment easier to reach, and nothing decorative
should sit between the working group and the priority it's hunting for.

Earn civic trust — credibility is the brand's core asset. Institutional clarity,
plain language, honest presentation of evidence, no persuasion tricks.

Distinguish agent from human — content authored by an AI agent must be visibly,
unmistakably marked as such (a hard requirement from the brief), because the
whole catalog's integrity depends on knowing who said what.

Scannability first — the working group scans, compares, and ranks. Hierarchy,
alignment, and consistent affordances matter more than any single flourish; a
member should be able to rank ten submissions at a glance.

Accessible as a civic obligation — this is public infrastructure, so access is
not a feature. Design to WCAG 2.1 AAA where feasible, AA as the floor.

## Accessibility & Inclusion

Target WCAG 2.1 AAA where feasible, with AA as the non-negotiable floor. That
means 7:1 contrast for body text where achievable (4.5:1 minimum), full keyboard
operability with visible focus, honored `prefers-reduced-motion`, semantic
landmarks, and color never used as the sole carrier of meaning (the agent/human
distinction in particular must survive without color). Plain-language copy serves
both the accessibility goal and the public audience.
