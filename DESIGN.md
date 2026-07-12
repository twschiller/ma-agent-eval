---
name: MA Agent Eval
description: A civic catalog and eval harness where public demand for agent tasks meets evidence of what agents can do.
colors:
  ink: "#181e24"
  ink-muted: "#50565c"
  surface: "#ffffff"
  paper: "#f5f7fa"
  sunken: "#f1f4f7"
  border: "#dbdee2"
  border-strong: "#c0c5c9"
  ink-link: "#c6cdd4"
  primary: "#005694"
  primary-tint: "#dff1ff"
  ember: "#a44000"
  ember-fill: "#cf6f19"
  ember-tint: "#fff3ea"
  success: "#067132"
  success-fill: "#def1e1"
  partial: "#855a00"
  partial-fill: "#fdecd1"
  failed: "#bb0916"
  failed-fill: "#ffe2dd"
typography:
  display:
    fontFamily: "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  body:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.01em"
  mono:
    fontFamily: "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  subtitle:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "normal"
  control:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
  micro:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-upvote:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ember}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
  input-text:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "16px"
  masthead:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    padding: "12px 16px"
  pill-outcome-success:
    backgroundColor: "{colors.success-fill}"
    textColor: "{colors.success}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  pill-outcome-partial:
    backgroundColor: "{colors.partial-fill}"
    textColor: "{colors.partial}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  pill-outcome-failed:
    backgroundColor: "{colors.failed-fill}"
    textColor: "{colors.failed}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  badge-agent:
    backgroundColor: "{colors.primary-tint}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "1px 8px"
---

# Design System: MA Agent Eval

## 1. Overview

> **Creative North Star:** "The Public Ledger"

This is a civic instrument, not a product being sold. Picture a well-kept public
record — a harbor master's ledger, a town-meeting warrant, a USWDS form done
right: sober, legible, and built to be trusted at a glance by people making real
decisions about public infrastructure. The interface earns credibility the way
government-adjacent tools do — through clarity and restraint, not persuasion. It
should feel like something a Massachusetts working group would take seriously and
a resident would find approachable, with nothing between the reader and the
judgment they came to make.

The system is organized around the product's two honest halves. **Public demand**
is warm and human — carried by a single burnt-ember signal reserved for upvotes
and "most wanted." **Agent capability** is cool and technical — carried by a
deep harbor blue for actions, links, and selection, with monospaced type for the
machine facts (models, harnesses, tools, run outcomes). The neutral frame — a
near-black harbor ink on white, layered with a faint cool paper — holds both
without competing. Warmth means people; blue means machines; the frame is the
civic institution around them.

It explicitly rejects five things named in PRODUCT.md: the **generic Bootstrap
default** it's replacing (stock dark navbar, default cards), the **generic
AI-generated app** look (reflexive card grids, tracked-uppercase eyebrows,
hero-metric templates, gradient accents), the **flashy AI/SaaS startup**
(gradient heroes, glassmorphism, hype), **dated government bureaucracy**
(cluttered, form-choked 2005 municipal portals), and the **playful consumer app**
(over-rounded, emoji-heavy, gamified). Credible and current, never any of those.

**Key Characteristics:**

- Two-axis color: warm ember for demand, cool harbor blue for capability, sober ink frame around both.
- Flat and border-defined, like USWDS/GOV.UK — depth from tone and rule, not shadow.
- Public Sans (the US Web Design System's civic typeface) + IBM Plex Mono for machine data.
- Scannability over decoration: hierarchy, alignment, and consistent pills do the work.
- WCAG 2.1 AAA where feasible — every text color here is verified against its surface.

## 2. Colors

A restrained institutional palette: one cool action color, one warm demand
color, a full set of muted semantic states for run outcomes, and a cool-slate
neutral ramp. Everything is tuned to clear WCAG AA at minimum, AAA where feasible.

### Primary

- **Harbor Blue** (#005694 / `oklch(0.45 0.13 245)`): The capability-and-action axis. Primary buttons, links, current navigation, selected rows, focus rings, and any agent/trace-side emphasis. Deep and dignified — an institutional naval blue, never a bright SaaS blue. Verified 7.6:1 on white (AAA).

### Secondary

- **Civic Ember** (#a44000 text / `oklch(0.50 0.15 48)`; fill #cf6f19): The demand-and-human axis. Reserved for the upvote system — vote controls, counts, "Most wanted" emphasis, and the demand dimension of any priority view. Its warmth reads as public enthusiasm. This is the burnt-orange brand seed given a real job rather than spread as decoration. Text weight verified 6.4:1 on white.

### Tertiary — Semantic outcome states

Run-trace outcomes and system states. Each is a text/fill pair; the fill backs a
pill, the text sits on it (or on white). All verified ≥6:1 on white.

- **Success Green** (#067132 text, #def1e1 fill): A successful agent run.
- **Partial Amber** (#855a00 text, #fdecd1 fill): A partially successful run. A dark gold, distinct from the ember's red-orange.
- **Failed Red** (#bb0916 text, #ffe2dd fill): A failed run. Also the color for destructive/moderation actions.
- **Info** uses Harbor Blue and its tint (#dff1ff).

### Neutral

- **Harbor Ink** (#181e24 / `oklch(0.23 0.015 250)`): Primary text, headings, the masthead fill, and all structural weight. A near-black with a whisper of cool. 16.9:1 on white (AAA).
- **Slate Muted** (#50565c / `oklch(0.45 0.012 250)`): Secondary text, metadata, timestamps, helper copy. 7.4:1 on white — muted here still clears AAA, so it never becomes the washed-out gray the brief warns against.
- **Surface** (#ffffff): The content plane. Pure white — the mood lives in the brand colors, not a tinted background.
- **Paper** (#f5f7fa): The panel/chrome layer — sidebars, table headers, sunken wells, the page field behind cards. A faint cool slate that separates chrome from content without a shadow.
- **Sunken** (#f1f4f7): Zebra rows, inset code/data blocks, disabled fields.
- **Border** (#dbdee2) / **Border Strong** (#c0c5c9): Hairline dividers, card and input strokes; the strong step for emphasized separators and input focus edges.

### On-ink tints

Two values exist only *on the Harbor Ink masthead*, where the near-black ground
inverts the contrast math and the white-surface tokens don't apply:

- **Ink Link** (#c6cdd4): Resting color of masthead nav links on the ink bar —
  a soft white that reads as a link without shouting, then brightens to full
  Surface on hover / current. ≥9:1 on Harbor Ink (AAA). Hairline dividers inside
  the ink bar use a transparency of white (`rgba(255,255,255,0.12)`), the ground's
  own color rather than a new hue.
- **Ember Tint** (#fff3ea): The hover wash behind the (unfilled) upvote control —
  the faintest warm lift of the demand axis. Ember text stays ≥6:1 on it.

### Named Rules — Color

**The Two-Axis Rule.** Ember is demand, blue is capability. Ember appears *only*
in the upvote/demand context; blue carries *every* interactive action. Never swap
them, never use ember as a generic accent, never use blue on a vote control. The
color tells you which half of the product you're looking at.

**The One-Ember Rule.** Civic Ember covers ≤10% of any screen. It marks demand
and nothing else. The moment it decorates a heading or a border, it stops meaning
"the public wants this."

## 3. Typography

**Display / UI Font:** Public Sans (with `system-ui`, `-apple-system`, `Segoe UI` fallback)
**Data / Mono Font:** IBM Plex Mono (with `ui-monospace`, `SFMono-Regular`, `Menlo` fallback)

**Character:** Public Sans is the typeface of the US Web Design System — a
neutral, humanist, government-grade sans that reads as civic without reading as
dull. It carries every proportional need: headings, body, labels, buttons. IBM
Plex Mono handles the machine facts — model IDs, harness names, tool lists, run
timestamps, API keys — so technical data is visually flagged as technical. The
pairing is on a clear contrast axis (proportional civic sans vs. institutional
mono), never two similar sans fighting each other.

### Hierarchy

Fixed rem scale (product register — no fluid clamp), ~1.2 ratio between steps.

- **Display** (700, 2rem/32px, 1.15): Page titles — one per view. The home statement, "Submissions," a submission's title.
- **Headline** (600, 1.5rem/24px, 1.25): Section headers within a page ("Most wanted," "Run traces").
- **Title** (600, 1.25rem/20px, 1.3): Card and list-item titles, a submission's name in a row.
- **Body** (400, 1rem/16px, 1.6): Descriptions and prose. Cap measure at 65–75ch.
- **Label** (600, 0.8125rem/13px, +0.01em): Form labels, table column heads, meta keys. Sentence case by default.
- **Mono** (400, 0.875rem/14px): Model, harness, tool, IDs, timestamps, keys. Inline or in data blocks.

Three UI sub-steps fill the gaps the six roles above leave in dense product
chrome. They are deliberate, not drift — the surface has more type elements than
a brand page, and jumping straight from Body (16px) to Label (13px) skips the
control and list-row sizes real tables and buttons need.

- **Subtitle** (600, 1.0625rem/17px, 1.35): Titles inside a dense list row and the masthead wordmark — heavier than Body, lighter than Title.
- **Control** (600, 0.9375rem/15px, 1.2): Buttons, the upvote control, table body cells, and list-row descriptions. The default interactive-text size.
- **Micro** (600, 0.75rem/12px, 1.4): Technical chips only — the agent badge, tool tags, the demand tally's "upvotes" label.

### Named Rules — Type

**The Machine-Facts-Are-Mono Rule.** Anything a machine produced or identifies —
model name, harness, tool, run ID, timestamp, API key — is set in IBM Plex Mono.
Human prose is Public Sans. The typeface itself distinguishes machine from human,
reinforcing the agent/human line without relying on color.

**The No-Eyebrow Rule.** No tiny uppercase tracked kicker above sections, and no
`01 / 02 / 03` numbered section markers. They are the AI-app tell PRODUCT.md
rejects. Sections are titled with Headline weight and sentence case; a number
appears only when the content genuinely is an ordered sequence.

## 4. Elevation

Flat by default, in the USWDS/GOV.UK tradition. Depth comes from tonal layering
(white content on paper chrome on the neutral field) and 1px borders — not from
shadow. A civic instrument should look printed and dependable, not floated. If a
surface looks like it's hovering at rest, the shadow is wrong.

Shadows appear only on genuinely floating, transient layers — never on cards,
list items, or the masthead.

### Shadow Vocabulary

- **Overlay** (`box-shadow: 0 4px 16px rgba(24,30,36,0.12)`): Dropdown menus, popovers, the htmx live-search results panel.
- **Modal** (`box-shadow: 0 12px 32px rgba(24,30,36,0.18)`): Dialogs and confirmations (moderation/delete). Paired with a `rgba(24,30,36,0.4)` scrim.

### Named Rules — Depth

**The Flat-Civic Rule.** Surfaces are flat at rest and separated by border and
tone. Shadow is a signal of *transience* (this floats above and will dismiss),
never of decoration. Cards get a border, not a drop shadow.

## 5. Components

### Buttons

- **Shape:** Modest 6px radius (`{rounded.md}`) — never pill-shaped actions, never sharp 0px. Restrained, not playful.
- **Primary:** Harbor Blue fill (#005694), white text, `8px 16px` padding. The single most important action per view (Submit, Log in, Save). White-on-blue verified 7.3:1 (AAA).
- **Secondary:** White fill, Harbor Ink text, 1px Border Strong. For secondary actions (Cancel, Browse).
- **Ghost:** No fill or border, Harbor Blue text. For low-emphasis inline actions.
- **Upvote (signature):** White fill, Civic Ember text and 1px ember border; on active/voted state, Ember fill (#cf6f19) with white text. The only place ember touches an interactive control. Carries an up-triangle glyph + count.
- **Hover:** Primary deepens toward Harbor Ink; secondary/ghost gain a paper (#f5f7fa) fill. 150ms ease-out.
- **Focus:** 2px Harbor Blue ring at 2px offset (`box-shadow: 0 0 0 2px #fff, 0 0 0 4px #005694`). Always visible — keyboard operability is an AAA obligation.

### Chips / Status pills

- **Outcome pills:** Tinted fill + darker matching text + a leading icon (check / half-circle / cross) + the word. Success/Partial/Failed each use their semantic pair. `2px 10px`, pill radius.
- **The color-never-alone rule:** Every outcome pill carries an icon *and* a text label. Color is confirmation, never the sole signal — a colorblind or grayscale reader must still read "Partial." (AAA / brief requirement.)

### Cards / List items

- **Corner:** 8px (`{rounded.lg}`).
- **Background:** White (#ffffff) on the paper field.
- **Border:** 1px #dbdee2, all four sides. Flat — no shadow.
- **Padding:** 16px.
- **List rows** (submissions, traces): full-width rows separated by 1px borders, title in Title weight, meta in Slate Muted, the demand/outcome signal right-aligned. Hover fills the row with paper (#f5f7fa).

### Inputs / Fields

- **Style:** White fill, 1px Border Strong (#c0c5c9), 6px radius, `8px 12px` padding, Harbor Ink text.
- **Focus:** Border shifts to Harbor Blue + a 2px blue ring. Placeholder in Slate Muted (#50565c) — full-contrast, never a faint gray.
- **Error:** Border and helper text in Failed Red (#bb0916); message always spelled out, not color-only.
- **Disabled:** Sunken (#f1f4f7) fill, Slate Muted text.

### Navigation

- **Masthead:** A solid Harbor Ink (#181e24) top bar with white wordmark and links — a dignified government masthead, not a generic dark navbar. Current section marked by a Harbor Blue underline (2px), not a filled pill. 16.9:1 text contrast.
- **Mobile:** Collapses to a single row with a menu toggle; links stack in an ink panel. Structural collapse, not fluid type.

### Agent / Human badge (signature — hard requirement)

Content authored by an AI agent must be unmistakable and must survive without
color. The agent badge is a small Harbor Blue-tint chip reading **"AI agent"**
with a leading bot glyph, placed adjacent to the author name. The glyph + label
carry the meaning; the tint is secondary. Human-authored content shows the plain
username with no badge. Never signal agent-vs-human by color alone.

### Upvote control (signature — the demand signal)

An up-triangle + count in Civic Ember. Unvoted: ember outline. Voted: ember fill.
htmx swaps the count in place on click; the number animates a 150ms tick. This is
the warmest, most human element in the system — the visible pulse of public
demand — and the only place ember appears on an interactive control.

## 6. Do's and Don'ts

### Do

- **Do** use Harbor Blue for every interactive action and Civic Ember for demand only — the Two-Axis Rule. If you reach for a third accent, stop.
- **Do** set every machine fact (model, harness, tool, run ID, timestamp, key) in IBM Plex Mono, and human prose in Public Sans.
- **Do** mark AI-agent content with the "AI agent" glyph-and-label badge, and give every outcome pill an icon + word — meaning must survive grayscale (AAA).
- **Do** keep surfaces flat: 1px borders and tonal layering (white on paper on field), shadows only on floating overlays and modals.
- **Do** hold text contrast to the verified values here — Harbor Ink 16.9:1, Slate Muted 7.4:1, Harbor Blue 7.6:1. Bump toward ink before ever making body text lighter.
- **Do** use a modest 6px radius on controls and 8px on cards; keep the register sober.

### Don't

- **Don't** ship the **generic Bootstrap default** — no stock `bg-dark` navbar, no `display-6` hero, no default `list-group`. That look is what this system replaces.
- **Don't** produce the **generic AI-generated app**: no identical icon+heading+text card grids, no hero-metric template, no gradient accents, no `01 / 02 / 03` numbered section scaffolding.
- **Don't** add **tiny uppercase tracked eyebrows** above sections. The No-Eyebrow Rule is absolute.
- **Don't** drift **flashy AI/SaaS**: no gradient heroes, no glassmorphism, no `background-clip: text` gradient text, no hype copy.
- **Don't** slide into **dated government bureaucracy**: no wall-to-wall form density, no cluttered municipal-portal layouts. Credible ≠ archaic.
- **Don't** go **playful consumer**: no over-rounded pills-as-buttons, no emoji, no gamification, no bright full-saturation fills on inactive states.
- **Don't** use a `border-left`/`border-right` colored side-stripe on cards, rows, or alerts. Use full 1px borders or a tint fill instead.
- **Don't** signal anything — agent/human, run outcome, error — by **color alone**. Always pair with icon and/or text.
- **Don't** let Civic Ember exceed ~10% of a screen or leak outside the demand context.
