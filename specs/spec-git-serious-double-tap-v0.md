# git-serious double-tap Plugin Specification

## Plugin Identity

- **Slug:** `git_serious_double_tap` (dist `git-serious-double-tap-tap`, namespace `tap_plugin.git_serious_double_tap`)
- **Display name:** git-serious double-tap
- **Initial page route:** `/double-tap`
- **Panel types:** `double-tap-demo-strip` (v0.2.0, incubated here — see [Demo Strip](#demo-strip)); everything else is git_serious's, mounted by edge
- **Initial page variables:** none

## Philosophy

A **double-tap** plugin is one built to introspect the TAP system and platform itself — TAP pointed
back at the people and machinery that build TAP. This one is git-serious pointed at
unified-systems-com, the GitHub organization the product is built in, so the CI/CD system on the
grid is our own.

The plugin exists to hold **only what is specific to that instance**: which pages and panels we
need to work a running example, in what arrangement, over which repositories. It is deliberately
thin. Every time working the example reveals a capability that any git-serious user would want —
a panel, a search, a projection, a vocabulary gap — that capability lands in `git_serious` or
`github_core`, and what stays here is the instance's choice to use it. The discipline is the same
one product-build sessions already follow: repeatable capability goes down, configuration stays up.

**In scope for v0:** a home page that composes existing git-serious panels by edge alone, proving
the instance-configuration shape works with zero code. **Out of scope:** models, edges, collectors,
and any page a second git-serious instance would also want.

**v0.2.0 amendment (2026-09-08, ruled by George):** a panel type MAY be incubated here when it has
no precedent anywhere in the system and the instance is the only place it can be made real —
the first card-level panel is the case. The incubator rule: make it work here against one real
organization, then lift the repeatable mechanism into tap_web (a card panel type) and leave the
instance-specific parts (the window, the criticality property) behind. An incubated panel is a
loan, not a residence; its spec section names the graduation issue.

## Goals

| # | Name | Description |
| :---: | --- | --- |
| 1 | Instance configuration lives in a plugin | The unified-systems-com pages are a versioned, installable plugin, not hand edits on one grid. |
| 2 | Compose, never copy | Pages here mount product panels by `USES_PANEL` edge; no panel, search or template is duplicated from git_serious. |
| 3 | Push repeatable capability down | Anything a second instance would want is built in git_serious or github_core, then used from here. |
| 4 | Zero code first | v0.1.0 shipped a manifest and GRIFT only, proving the shape before any Python. Python arrives only under the incubator rule (Philosophy), never as a permanent home. |

## Requirements

| RID | Name | Status | Notes |
| --- | --- | :---: | --- |
| req-git-serious-double-tap-scope | [Instance-Only Scope](#instance-only-scope) | Implemented | Manifest + GRIFT only; install dep on git_serious; no models, edges, collectors or panel types |
| req-git-serious-double-tap-page-home | [Home Page](#home-page) | Implemented | `/double-tap` is the demo strip alone; `/double-tap/status-wall` mounts git-serious's status wall and not-observed panels by edge |
| req-git-serious-double-tap-page-strip | [Demo Strip](#demo-strip) | Implemented | One card per repository that moved in the last 24 hours: its open PRs with the check results of each PR's current head; collection freshness said out loud; navigation to the four git-serious views |
| req-git-serious-double-tap-nongoals | [v0 Non-Goals](#v0-non-goals) | Implemented | What this plugin refuses to grow into |

### Instance-Only Scope
----
RID: `req-git-serious-double-tap-scope`

Status: `Implemented`

The plugin contributes no TAP-managed entity types of its own: no models, no edge definitions, no
collectors, no panel types. Default dimensions are therefore not applicable; the page nodes it
seeds are core `page` entities and carry the core `tap.graph: web` dimension like every other page.
Its only install dependency is `git-serious-tap` (pyproject `dependencies`), because its GRIFT
edges target entity ids git_serious seeds. That is an install-and-seed-order dependency, declared
where install deps live and enforced by boot-profile population order (git_serious's `seed-plugin`
step precedes this plugin's), not a code `depends_on` — nothing here imports git_serious's Python.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-scope-1 | No Vocabulary | Implemented | The manifest declares no `[models]` or `[edges]`; `manage.py plugins` reports `models=0/0 edges=0/0` for the plugin. | |
| req-git-serious-double-tap-scope-2 | Install Dep Declared | Implemented | `pyproject.toml` lists `git-serious-tap` under `dependencies`; the manifest's `depends_on` is empty. | Install dep, not import dep. |
| req-git-serious-double-tap-scope-3 | Seeds After git_serious | Implemented | Every boot profile that seeds this plugin lists its `seed-plugin` step after git_serious's. | The importer warns, not fails, on a dangling endpoint — so order is the guard. |

### Home Page
----
RID: `req-git-serious-double-tap-page-home`

Status: `Implemented`

Two pages, minimal by design (George, 2026-09-09: "only exactly the pieces of content we care
about right now — the cards").

| Route | Nav weight | Content |
| --- | :---: | --- |
| `/double-tap` | 110 | The [demo strip](#demo-strip) and nothing else: the cards, the collection's freshness, four links. |
| `/double-tap/status-wall` | 111 | git-serious's status wall (every workflow's latest run) and the not-observed workflows, mounted by `USES_PANEL` edge — the drill-down the strip links to. |

The gates panel left the landing in v0.3.0; the gate view (`/git-serious/gate`) is one of the four
links. The landing carries no search or projection of its own; its one panel is the incubated
strip. It is the running example's first screen and the place target-3 pages (map
unified-systems) attach as they are found.

#### Implementation

`tap_plugin/git_serious_double_tap/grift/home.grift.json` — one batch (v0.3.0): two page nodes
(`/double-tap` `01a081d1-f90f-76ff-b882-491af67b9d4b`, `/double-tap/status-wall`
`01a08670-50b0-76d7-9593-26d6dd016f7a`), the strip panel node (`01a08375-96e8-77ea-bf33-1d07f1ed54cc`,
slug `double-tap-demo-strip`) and three `USES_PANEL` edges. Panel targets: status wall `01a0632f-38b6-7440-9de9-3d5a3dadeb2a`, not-observed
`01a0632f-38b6-7440-9de9-3d5ba8eadfc4`, gates `01a067e1-8266-71e1-bb86-fba4947ee6a2` (from
git_serious's `landing.grift.json`; ids are stable across its re-publishes).

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-page-home-1 | Routes Serve | Implemented | `GET /double-tap` renders the strip slot alone; `GET /double-tap/status-wall` renders the two git_serious slots; both 200 on a booted git_serious instance with this plugin seeded. | |
| req-git-serious-double-tap-page-home-2 | Composition Plus One | Implemented | The bundle's nodes are the two pages and the strip panel; every other edge targets a git_serious-seeded panel, and the import reports no dangling edge when git_serious seeded first. | v0.1.0 read "only node is the page"; superseded by the incubator rule. |

### Demo Strip
----
RID: `req-git-serious-double-tap-page-strip`

Status: `Implemented`

Issue: unified-systems-com/git-serious-double-tap#6 (Codex brief 2026-09-08, cut by George to
"strip only, fixed 24-hour window, no pins"). Graduation issue: the card mechanism into tap_web —
filed when the second card panel appears, not before.

The first screen of the running example: which repositories are moving toward the demo, their
open pull requests, and which checks pass or fail on each PR's **current head**. Cards wrap like
columns of text — nothing scrolls sideways (v0.3.0; v0.2.0 was one scrolling row). Below the cards,
links to the four views (organization, repository machinery, the gate, the status wall page).

**A workboard, not a dashboard** (v0.4.0, George 2026-09-09): the reader is here to perform work,
so the board presents opportunities for action. Three levels for the eye, in the order the viz
system already teaches — the board, then the order of the cards, then one card:

1. **The board** — a title, the collection's freshness, and one summary line counting the cards
   by state in board order (*needs a fix · cannot be seen · waiting on checks · green, review it ·
   quiet*). The overview before the detail (Shneiderman's mantra).
2. **The order** — a row-major grid so the first card is top-left and reading continues left to
   right; criticality first, then movement, then name (unchanged). Cards wrap; nothing scrolls.
3. **One card, a universe to itself** — a surface with an edge and a state rail (the preattentive
   cue), the repository in small caps with its criticality chip, then the **nudge**: one line with a
   verb and the PR numbers it points at, self-contained enough to act on from the card alone
   (*Fix 2 failing checks on #83* · *Look — checks not observable on #7* · *Wait — 3 checks still
   running on #7* · *Review — #344 green* · *nothing open — latest merge #55*), then the rows.

Nudge precedence is by what the reader must do, worst first: failed > not observable > pending >
green > quiet. *Green* deliberately says *review it*, never *merge*: passing checks do not
establish approval, conflicts or merge readiness (the hover says so). Colour is spent only on
state — red, ochre, green, violet for not-observable — and every state also carries a glyph and a
word. Kept from the Tufte pass: hairlines inside a card, small caps for the name, tabular digits,
and no chrome that says nothing about a repository. The design fundamentals behind these choices
(attention allocation, preattentive cues, alarm rationalization, situation awareness, pull work)
are written up in the double-tap workboard briefing (docs, 2026-09-09) and summarized in
[Design fundamentals](#design-fundamentals).

#### Implementation

`tap_plugin/git_serious_double_tap/panels/demo_strip/__init__.py` — panel type
`double-tap-demo-strip` (registered in `apps.py`), reads through `execute_gryphon_raw` over four
declared queries (repositories, pull requests, the `PROPOSES_COMMIT` join, collection jobs) and
folds them in pure functions (`build_cards`, `dedupe_checks`, `classify_check`, `_summarize`,
`board_summary`, `collection_status`); template `templates/git_serious_double_tap/panels/demo_strip.html`; styles
`static/git_serious_double_tap/css/demo_strip.css`. No github_core or git_core Python is imported —
`depends_on` stays empty; the queries name those plugins' node types, a data dependency the boot
record already orders. Data contract: github_core ≥ the release that ships `pull_request`
(github-core#82 / PR# 83) and `custom_properties` (PR# 81).

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-page-strip-1 | Movement Selects | Implemented | Opened, merged, head-commit date and a running check qualify; `updated_at` alone does not; a PR without a repository node on the grid is not a card. | `test_demo_strip.py::test_repository_qualifies_by_opened_merged_or_head_commit_only`, `test_running_check_counts_as_movement_now`, `test_pull_request_without_a_repository_node_is_not_a_card` |
| req-git-serious-double-tap-page-strip-2 | Criticality Orders | Implemented | critical > high > medium > low > unclassified, then recency, then name; unset, out-of-range and unobservable all read unclassified with distinct notes. | `test_criticality_orders_then_recency_then_name` |
| req-git-serious-double-tap-page-strip-3 | Current Head, Reruns Collapsed | Implemented | Distinct (app, name) keeps the highest `check_run_id`; passed is a count, failed then pending are names, other keeps its word. | `test_rerun_replaces_the_run_it_reran`, `test_row_buckets_passed_failed_pending_other`, `test_unknown_words_are_kept_not_dropped` |
| req-git-serious-double-tap-page-strip-4 | Three Observability States | Implemented | unobservable / none / observed render distinct text and none reads green; a merge-only repository shows the latest merge number. | `test_check_observability_three_states_never_read_green`, `test_merged_only_repository_shows_latest_merge_and_no_rows` |
| req-git-serious-double-tap-page-strip-5 | Freshness Said | Implemented | never / fresh / stale / failed from the github_core collection jobs only; never-succeeded outranks failed. | `test_collection_line_four_states`, `test_collection_line_ignores_other_collectors` |
| req-git-serious-double-tap-page-strip-7 | One Nudge Per Card | Implemented | Every card carries exactly one state, verb and headline by the precedence failed > unobservable > pending > green > quiet; the board's summary line counts cards by state in that order with zeros omitted. | `test_card_state_and_nudge_precedence`, `test_board_summary_counts_in_board_order_without_zeros` |
| req-git-serious-double-tap-page-strip-6 | Live | Implemented | On the 8010 grid after a collection (2026-09-08): five cards, critical → high → unclassified, PR rows with passed counts and pending names, collection line fresh. | Observed by hand; a boot-and-test lane for this repo is #4. |

### Design Fundamentals
----
*Not a requirement — the standing rationale behind req-git-serious-double-tap-page-strip, so the
next pass argues with the principles rather than with taste. Prior-art search 2026-09-09.*

| Field | Principle | What it decides on this board |
| --- | --- | --- |
| Attention allocation (Wickens, SEEV) | Where the eye goes = salience + expectancy + value − effort. Design rule: correlate salience with value, expectancy with effort. | The most valuable card is first and most salient (rail + verb); every card shape is identical so the expected place for the nudge costs no effort. |
| Preattentive processing & Gestalt (Healey; Few) | Colour hue, a single distinct glyph, enclosure and proximity are read before conscious attention; one attribute at a time. | State is ONE hue plus ONE glyph on the rail and the nudge; enclosure (the surface) groups a repository; the hairline separates rows without a second colour. |
| Alarm management (ISA-18.2 / EEMUA 191) | Every alarm reaching an operator is one they can and should act on; reserve high priority for a small set; rationalize away nuisance; a flood is >10 in 10 min. | The nudge is an alarm with a verb; *quiet* and *green* are demoted below the actionable states; the summary line is the flood meter. |
| Situation awareness (Endsley) & skill/rule/knowledge behaviour (Rasmussen) | Perceive → comprehend → project; rule-based response needs the cue to name the rule. | Summary (perceive) → card order (comprehend) → nudge (the rule: Fix/Look/Wait/Review) → rows (project what happens next). |
| Visual information seeking (Shneiderman) & dashboards (Few) | Overview first, zoom and filter, details on demand; one screen, glanceable, simplicity. | Board → card → rows → links to GitHub and the status wall page are the four zoom levels; the strip stays one screen. |
| Pull work (Kanban; Anderson) | Make work visible, limit work in progress, pull the next item from the top. | Cards are the visible work; criticality-then-recency is the pull order; a WIP limit and an *acknowledged* state are the open questions. |
| Signifiers & heuristics (Norman; Nielsen) | Visibility of system status; match the real world; signifiers say what is possible. | The collection line is system status; the nudge is written in the reader's verbs; links look like links, results look like results. |
| Motor and choice cost (Fitts; Hick) | Fewer, larger targets; fewer choices per decision. | One primary link per row; one verb per card; four navigation links, not a menu. |

Open questions this rationale surfaces (their own issues when picked up): order within a
criticality by actionability rather than recency; a work-in-progress cap on the board; an
*acknowledged* state so a nudge can be silenced without hiding the card; whether a repository
with nothing actionable belongs on the board at all.

### v0 Non-Goals
----
RID: `req-git-serious-double-tap-nongoals`

Status: `Implemented`

- No models, edges or collectors — if one is needed, it is built in git_serious or github_core
  and used from here. A panel type only under the incubator rule (Philosophy), with its
  graduation named in its spec section.
- No boot record of its own: the instance boots git-serious's record with this plugin added to
  the install and population sections.
- No second-instance generality: a page that any git-serious user would want is a git_serious page.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-nongoals-1 | Stays Thin | Implemented | The runtime package contains no `models/`, `edges/` or `collectors/` directory; `panels/` and `templates/` hold only incubated panels whose spec sections name a graduation. | Reviewed on every PR. v0.1.0 also forbade `templates/`; relaxed 2026-09-08. |
