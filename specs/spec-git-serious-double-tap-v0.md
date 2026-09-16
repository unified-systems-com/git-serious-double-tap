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
| req-git-serious-double-tap-page-home | [Home Page](#home-page) | Implemented | `/double-tap` is the demo strip and, under it, the nightlies board; `/double-tap/status-wall` mounts git-serious's status wall and not-observed panels by edge |
| req-git-serious-double-tap-page-tap | [The tap Page](#the-tap-page) | Implemented | `/double-tap/tap`: one page node mounting git-serious's shared repository panels by id, each edge pinning `repo=unified-systems-com/tap` as a fixed input (tap#359) — the instance's one scoped page, owning one panel of its own, the machinery panel (req-git-serious-double-tap-tap-projection) |
| req-git-serious-double-tap-tap-projection | [The tap Projection](#the-tap-projection) | Implemented | A double-tap-owned projection whose one elevation runs github_core's machinery layout and then the tap lanes layout on the same canvas; the tap page's machinery panel owns it |
| req-git-serious-double-tap-page-strip | [Demo Strip](#demo-strip) | Implemented | Top Movers: one card per repository that moved in the selected window (all open · last week · last 24 hours; selector upper-right, default 24h): its open PRs with the check results of each PR's current head; collection freshness said out loud |
| req-git-serious-double-tap-page-nightlies | [Nightlies](#nightlies) | In Development | One card per repository that runs on a schedule; each scheduled workflow's LATEST run — red when it failed, and NOT OBSERVED when nothing ran in the window. Where a red nightly is read (operator ruling 2026-09-14: the landing page, not an inbox) |
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
| `/double-tap` | 110 | **Top Movers** (renamed 2026-09-14, #42; the URL is unchanged): the [demo strip](#demo-strip) — the cards for the selected window, the collection's freshness, the window selector — and under it the [nightlies board](#nightlies) (v0.5.0): every scheduled workflow's latest run, worst first. |
| `/double-tap/status-wall` | 111 | git-serious's status wall (every workflow's latest run) and the not-observed workflows, mounted by `USES_PANEL` edge — the drill-down the strip links to. |
| `/double-tap/tap` | 112 | [The tap page](#the-tap-page): the repository that builds TAP, on the generic repository page's structure with hardcoded scope. |

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
| req-git-serious-double-tap-page-home-1 | Routes Serve | Implemented | `GET /double-tap` renders the strip slot and, under it, the nightlies slot (v0.5.0); `GET /double-tap/status-wall` renders the two git_serious slots; both 200 on a booted git_serious instance with this plugin seeded. | |
| req-git-serious-double-tap-page-home-3 | Named Top Movers | Implemented | The page node and the strip panel node are named `Top Movers` (home bundle v0.4.0); the route stays `/double-tap`. | #42 |
| req-git-serious-double-tap-page-home-2 | Composition Plus One | Implemented | The home bundle's nodes are the two pages and the two double-tap panels (the strip, the nightlies board); every other edge targets a git_serious-seeded panel, and the import reports no dangling edge when git_serious seeded first. | v0.1.0 read "only node is the page"; superseded by the incubator rule. |

### The tap Page
----
RID: `req-git-serious-double-tap-page-tap`

Status: `Implemented`

Issue: unified-systems-com/git-serious-double-tap#9 (George, 2026-09-09). The product ships a generic
per-repository page (`/git-serious/repository?repo=owner/name`, git-serious-tap#56 / PR# 58) whose
every search takes `repo` as a required input. The instance is permitted what the product is not:
**one page with hardcoded scope**. `/double-tap/tap` is that page for unified-systems-com/tap, the
repository that builds TAP.

**Structure** — the same five rows as the generic page, in the same order: identity, machinery,
open pull requests, the status wall, the not-observed workflows. They are not copies: they are the
generic page's panel nodes (git-serious repository bundle) and the landing's wall and not-observed
panel nodes, mounted by id. A reader who knows one page knows the other because it IS the other,
narrowed.

**Scope** — each `USES_PANEL` edge carries `properties.inputs = {"repo": "unified-systems-com/tap"}`
(tap#359): when the page builds a slot's panel address it lays that fixed input over the URL's
query string, so the panel's searches receive `repo` exactly as they would from
`?repo=unified-systems-com/tap` on the generic page. The fixed input wins: `?repo=` on this page is
ignored, not honoured. `?state=` passes through as on the generic page. The bundle declares no
search and no `$`; the scope lives on five edges, in one literal each — the one place the instance
is allowed to be specific (ruled by George 2026-09-09: repository views are one panel, consumed
through searches and page/panel variables, never copied).

**Divergence** — with no copied searches the seam moves to the projection: a tap-specific machinery
view is a double-tap-owned graph panel (its own `USES_PROJECTION`, sharing git_serious's scene
searches by id) swapped into the `machinery` slot — one panel the page would then own, the other
four stay shared. Until that panel exists the slot mounts git-serious's machinery panel. What the
v0.1.0 copy cost — polish landing on one page and not the other — is what this shape removes.

**Card link** — the tap card on /double-tap opens this page; every other card opens the generic page
(`REPO_PAGE_OVERRIDES` in the strip panel — the one place a card link is allowed to be specific).

#### Implementation

`tap_plugin/git_serious_double_tap/grift/tap-repository.grift.json` — one batch: the page node
(`/double-tap/tap`, nav weight 112) and five `USES_PANEL` edges whose targets are out-of-file
endpoints — git-serious's identity, machinery and open-pull-requests panels (repository bundle
`01a08766-…`) and the landing's status wall and not-observed panels (`01a0632f-…`) — each with
`properties.inputs.repo`. Registered in the manifest's `[grift]` table as `tap_repository`. v0.1.0
carried five panels, six searches and thirteen edges as copies; v0.2.0 retired them
(`--force-batches … --sweep-strict`).

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-page-tap-1 | Same Structure | Implemented | `GET /double-tap/tap` renders the five slots in the generic page's order and every panel returns rows for unified-systems-com/tap; each slot's fragment URL carries the git-serious panel's entity id (the same id the generic page mounts) with `repo=unified-systems-com%2Ftap`. | Observed 2026-09-09 on 8010 with tap PR# 362 (tap#359) merged into the session core: identity 1 row, pulls, wall 274 ids, not-observed 14 — every slot's fragment URL ends `?repo=unified-systems-com%2Ftap`; identity/pulls/wall/not-observed carry git-serious's panel ids, the machinery slot the double-tap machinery panel (-3, in progress). |
| req-git-serious-double-tap-page-tap-2 | Pinned Scope | Implemented | The bundle declares no search and no panel; every `USES_PANEL` edge carries `inputs.repo = "unified-systems-com/tap"`; `?repo=other` on the page changes nothing (the fixed input wins). | The one literal per edge is the instance's privilege. Observed 2026-09-09: the bundle has 1 node, 5 edges, no `$`; the fixed input wins over the URL (tap#359's ACIDs). |
| req-git-serious-double-tap-page-tap-3 | Divergence Seam Is The Projection | Implemented | A tap-specific machinery view arrives as a double-tap-owned graph panel with its own `USES_PROJECTION` over git_serious's scene searches, swapped into the `machinery` slot; nothing else is copied. | Not built; the slot mounts git-serious's machinery panel today. Implemented 2026-09-09 by PR# 13: the machinery slot is `double-tap-tap-machinery`, the one panel the page owns (req-git-serious-double-tap-tap-projection). |
| req-git-serious-double-tap-page-tap-4 | Card Link | Implemented | The tap card's repository link is `/double-tap/tap`; any other repository's is the generic page. | `test_card_links_to_the_git_serious_repository_page` |

### The tap Projection
----
RID: `req-git-serious-double-tap-tap-projection`

Status: `Implemented`

Issue: unified-systems-com/git-serious-double-tap#12 (George, 2026-09-09: "let's build the first cut of the
tap projection"). This is the divergence seam the tap page promised: **machinery edits** live in
github_core (machinery.js and its config keys, the nesting rules it feeds); **tap-specific edits**
live here. Nothing of machinery.js is copied.

**Composition** — the double-tap seeds a projection, an elevation and a layout of its own. The
elevation's ordered layouts are `[git-serious-landing-layout, double-tap tap lanes layout]`: the
first is git_serious's existing layout entity (github_core's machinery.js) referenced by entity id
across the bundle boundary, the second is this plugin's `tap-machinery.js`. Per
req-viz-layout-execution the two run serially on the same canvas, so the tap layout sees every
position, `_stage` / `_order` datum and class the base left behind, and builds on them. The
projection keeps the base's declarative surface (the `machinery` config block, icon-badge node
style, the two search-driven badge sets). One graph panel (`double-tap-tap-machinery`) owns the
projection and shares the generic repository page's three scene searches by id; the tap page's
`USES_PANEL` edge mounts it with the fixed input `repo=unified-systems-com/tap`.

**What the tap layout adds** (first cut, the cardinal map ruled 2026-09-09):

1. *Lanes by what starts it.* Each workflow's primary trigger — pull_request / merge_group >
   push > workflow_run > schedule > workflow_call > workflow_dispatch — puts it in one of five
   lanes: **gate**, **publish**, **scheduled**, **fleet**, **baseline**. A workflow_call workflow
   whose callers span more than one lane is the reusable baseline; one called from a single lane
   or from other repositories is fleet. A workflow_run workflow inherits its upstream's lane. A
   dispatch-only workflow takes the lane of the first local workflow it calls. GitHub's dynamic
   workflows (CodeQL, the Copilot reviewers) sit in the gate lane.
2. *The cardinal map.* Inside the repository box: the gate lane centre-right, publish to its left
   (artifacts on the left), scheduled below, fleet then the baseline at the bottom. Sources stay on
   the right and outputs on the left; the layout re-seats them around the new block rather than
   re-laying them out. Lanes are synthetic compound parents so each band carries its label; the
   gate lane is drawn heavier than the rest.
3. *Cross-lane relationships.* `uses:` of a local reusable workflow and `workflow_run` chaining
   become synthetic dashed / dotted edges between workflow boxes.

Nothing in the module names tap: the lanes are derived from the collected workflow
configuration (`triggers`, `jobs[].uses`, `workflow_run`), so the same module reads any
repository and only the page pins which one. Warnings, never silence, for an unresolved upstream,
a workflow with no observed trigger, or a scene with no repository.

#### Implementation

`tap_plugin/git_serious_double_tap/grift/tap-machinery.grift.json` — projection
`01a08804-4b2c-766d-9dec-9cad99504f85`, elevation `…9caec624cdb0`, layout `…9caf6fb0a0ee`, panel
`…9cb0630013cf` (slug `double-tap-tap-machinery`), edges `USES_ELEVATION`, `USES_DEFAULT_ELEVATION`,
two `USES_LAYOUT` (the first onto git_serious's `01a03f78-11fa-7029-823d-7946a31a3ee2`),
`USES_PROJECTION`, three `USES_SEARCH` onto the generic page's scene searches. Registered in the
manifest as `tap_machinery`, before `tap_repository`, whose machinery `USES_PANEL` edge now targets
this panel. Module:
`tap_plugin/git_serious_double_tap/static/git_serious_double_tap/js/projections/tap-machinery.js`.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-tap-projection-1 | Two Layouts, One Canvas | Implemented | The tap elevation lists git_serious's machinery layout first and the tap lanes layout second; the panel's projection context on 8010 names both `js_file`s in that order. | Observed 2026-09-09. |
| req-git-serious-double-tap-tap-projection-2 | Nothing Copied | Implemented | The bundle contains no layout whose `js_file` is machinery.js; the base layout is referenced by entity id. | Reviewed on every change. |
| req-git-serious-double-tap-tap-projection-3 | Lanes From Data | Implemented | The module classifies from `configuration.triggers`, `jobs[].uses` and `workflow_run` only; no repository, workflow or job name appears in it. | Reviewed; a JS test harness is a follow-on (no node on the host). |
| req-git-serious-double-tap-tap-projection-4 | Page Mounts It | Implemented | `/double-tap/tap`'s machinery slot is `double-tap-tap-machinery`; the fragment with the pinned repo returns the tap projection and the scene. | Observed 2026-09-09; pinned inputs themselves are tap#359. |
| req-git-serious-double-tap-tap-projection-5 | Seen By A Human | In Development | The five lanes render in the cardinal order on /double-tap/tap with the call edges visible. | George to confirm on the 8010 stack. |

### Demo Strip
----
RID: `req-git-serious-double-tap-page-strip`

Status: `Implemented`

Issue: unified-systems-com/git-serious-double-tap#6 (Codex brief 2026-09-08, cut by George to
"strip only, fixed 24-hour window, no pins"). Graduation issue: the card mechanism into tap_web —
filed when the second card panel appears, not before.

The first screen of the running example: which repositories are moving toward the demo, their
open pull requests, and which checks pass or fail on each PR's **current head**. Cards wrap like
columns of text — nothing scrolls sideways (v0.3.0; v0.2.0 was one scrolling row). Nothing below the
cards: the strip is the board, not a site map — the views are the top navigation's (v0.4.1, #17
dropped the four standalone links).

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

**The window** (v0.4.0, George 2026-09-14, #42): the strip is *Top Movers* and the reader picks the
window in the upper-right — *All open*, *Last week*, *Last 24 hours* — as `?window=all|7d|24h` on the
page's query string, which the slot's auto-refresh URL already carries. The default is 24 hours, so
the page reads as before until someone clicks. `7d` and `24h` are the same movement rule (opened,
merged, head pushed, building now) over a wider span; `all` is *any open pull request*: a card per
repository with one or more OPEN PRs, no time filter, and merged-only quiet cards drop out because
nothing is open. An unknown value falls back to the default and says so on the strip — bad input is a
state, never a blank.

**The board** (v0.5.0, George 2026-09-09, second cut): the movers are placed, not listed. Row one is
the platform, unified-systems-com/tap, alone and centred at half the width — the parent gets its own
row. Row two, under a hairline and the heading *Products*, holds the products across the width
(git-serious, samsite), each its own card or a one-line *nothing open*. Row three is the *Plugins*
board: every other mover that is not support or fixtures, left to right by state (failed, not
observable, waiting, green) and then criticality, wrapping. Support and fixture repositories get a
*Support* row last. Movers only: a card exists because it moved; the board only decides where it
sits. A product → plugin mapping was built and dropped the same evening: the columns it made were
not space-efficient, and deriving it would have meant an ad-hoc collector addition.

The products row is a **declared list**, not the org's `repository-role` property (which says
samsite is a plugin and git-serious-double-tap a product). The page carries a note-to-self pointing
at Issue# 21 - git-serious-double-tap until the row is derived. The collection line shows the
viewer's local time.

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
`double-tap-demo-strip` (registered in `apps.py`), resolves the window from the request (`resolve_window`,
`WINDOWS`), reads through `execute_gryphon_raw` over four
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
| req-git-serious-double-tap-page-strip-8 | The Board | Implemented | Platform row; the declared products across their row; the plugins board ordered state-then-criticality; a support row; the note-to-self naming Issue# 21. | `test_board_places_platform_products_plugins_and_support` |
| req-git-serious-double-tap-page-strip-9 | Three Windows | Implemented | `?window=24h` (default) and `7d` apply the movement rule over their span; `all` yields a card per repository with an open PR and none for merged-only; the selector marks the active window and keeps other query parameters; an unknown value renders the default with a note. | `test_last_week_window_widens_the_same_rule`, `test_all_window_is_every_open_pull_request_and_nothing_closed`, `test_resolve_window_default_selection_and_fallback` |
| req-git-serious-double-tap-page-strip-6 | Live | Implemented | On the 8010 grid after a collection (2026-09-08): five cards, critical → high → unclassified, PR rows with passed counts and pending names, collection line fresh. | Observed by hand; a boot-and-test lane for this repo is #4. |

### Nightlies
----
RID: `req-git-serious-double-tap-page-nightlies`

Status: `In Development`

Issues: unified-systems-com/tap#137 (the nightly fuzz campaign reds its run — this is where the
red is read), unified-systems-com/tap#440 (the not-observed state: a nightly that never fired must
not look green). Ruled 2026-09-14 by the operator after an issue-filing reporter was built and
withdrawn: *"that's our nerve center and I'd rather work it in there than a new page I won't look
at."* The second card panel — and so the graduation trigger the strip's requirement named for
the card mechanism into tap_web (filed with this panel's first live sighting, not before).

**What it answers.** Did every nightly run, and did it pass? github_core already collects every
workflow run in the organization (`github_actions_run`: event, conclusion, start time) and every
workflow's declared triggers, so the board is a fold over data on the grid: one card per repository
that declares a scheduled workflow or has run one, one row per such workflow, each row that
workflow's **latest scheduled run**.

**Five row states, worst first** — the summary line, the card order and the row order all follow it:

| State | Reads | When |
| --- | --- | --- |
| `failed` | ✕ red | latest scheduled run in the window concluded `failure` / `timed_out` / `action_required` / `startup_failure` |
| `not_observed` | ? not observed | no scheduled run in the window — declared but never run, or last run older than the window; the last verdict is said in the detail, never promoted |
| `pending` | ◷ running | latest run is queued or in progress |
| `other` | ⊘ other | any other conclusion (`cancelled`, `skipped`, …), shown WITH its word |
| `green` | ✓ green | latest run in the window concluded `success` |

A card's state is its worst row. The window is 26 hours (a nightly is due once a day; GitHub delays
and drops on-the-hour crons), configurable per instance. Freshness is said on the board exactly as
the strip says it — the collection line — because the window is measured against the data's age
as well as the clock: a nightly that ran after the last collection is not here yet, and the board
says so rather than showing yesterday's green as today's.

**Why not an inbox.** Prior art (2026-09-14): failure e-mails to a workflow's actor, dashboards
(TestGrid, toolstate, waterfalls), chat alerts, and issue-on-failure bots. TAP is a dashboard-shaped
product that already collects the runs; the board is that family, with zero new mechanism. The
honest cost, named: latency is the collector's cadence, not the run's — the issue route had none.

#### Implementation

`tap_plugin/git_serious_double_tap/panels/nightlies/__init__.py` — panel type `double-tap-nightlies`
(registered in `apps.py`), reads through `execute_gryphon_raw` over three declared queries (scheduled
runs with their `EXECUTES_WORKFLOW` workflow; repositories with their `DEFINES_WORKFLOW` workflows,
whose `configuration.triggers` carries the declared `schedule`; collection jobs) and folds them in
pure functions (`build_cards`, `classify_run`, `board_summary`); reuses the strip's `collection_status`,
`_age`, repository-page routing and `_fetch`. Template `templates/git_serious_double_tap/panels/nightlies.html`
+ `_nightly_card.html`; styles ride `demo_strip.css` plus `nightlies.css` (the nightly states only).
Instance: the `Nightlies` panel node (`01a0a153-17c3-77da-8890-ef2ff52aef4a`, slug `double-tap-nightlies`,
`config.window_hours: 26`) mounted at `/double-tap` row-2 by `USES_PANEL`
(`01a0a153-17c3-77da-8890-ef30246ef097`), in `home.grift.json` v0.5.0. No auto-refresh script: a
nightly changes once a day, and a second copy of the strip's script is the graduation trigger, not
a thing to duplicate. No github_core Python is imported — `depends_on` stays empty.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-page-nightlies-1 | Scheduled Only | Implemented | A workflow is a row when it declares `schedule` or has a scheduled run; other workflows are not; a workflow whose repository is not on the grid is not a row. | `test_only_scheduled_workflows_are_on_the_board`, `test_a_workflow_with_scheduled_runs_but_no_declared_trigger_is_still_on_the_board`, `test_a_workflow_whose_repository_is_not_on_the_grid_is_not_a_row` |
| req-git-serious-double-tap-page-nightlies-2 | Latest Run, Five States | Implemented | The newest scheduled run by start time decides the row; failed / running / other-with-word / green from its status and conclusion; unknown words are kept, never dropped. | `test_latest_scheduled_run_wins`, `test_running_and_other_states`, `test_classify_run_five_states_and_unknown_words_kept` |
| req-git-serious-double-tap-page-nightlies-3 | Not Observed Never Green | Implemented | A declared schedule with no run, or a run older than the window, reads not observed; the old run's verdict is said in the detail and its link kept; the window is configurable. | `test_declared_schedule_with_no_run_is_not_observed_never_green`, `test_a_run_older_than_the_window_is_not_observed_and_says_what_was_last_seen`, `test_window_is_configurable` |
| req-git-serious-double-tap-page-nightlies-4 | Worst First | Implemented | Card state is the worst row; cards order worst-first then name; rows the same; the summary counts workflows by state in that order, zeros omitted; card links go to the repository view (tap's override kept), rows to the latest run. | `test_card_state_is_the_worst_row_and_cards_order_worst_first_then_name`, `test_card_links_to_the_repository_page_with_the_tap_override` |
| req-git-serious-double-tap-page-nightlies-5 | Live | Implemented | Seen on a spawned stack from this branch's boot pointer after one real collection (2026-09-14, 215 runs / 70 scheduled): 17 cards, 6 not-observed rows, the collection line present, zero console errors. The not-observed rows were tap's six nightlies — the collector's `initial_run_limit` (10 per repository) did not reach them on a fresh instance, the caveat named above, observed. No red row that night: the grid's one failed scheduled run had been superseded by a success on the same workflow, which is the correct reading. | Positive control held: a nightly with no run in the window shows `?`, never `✓`. The first render was blank — the included card template lacked its own `{% load tap_time %}` — a class the fold tests cannot see; the template now loads it. Red-row rendering is pinned by the fold tests and the CSS; its first live sighting is the next failed nightly. |

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
| Motor and choice cost (Fitts; Hick) | Fewer, larger targets; fewer choices per decision. | One primary link per row; one verb per card; no navigation menu of its own (#17). |

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
