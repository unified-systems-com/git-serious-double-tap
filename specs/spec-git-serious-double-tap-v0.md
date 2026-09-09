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

**Typography** (v0.3.0, the Tufte pass): a serif page, hairline rules instead of boxes, no fills
and no badges; the repository name in small caps, criticality as a word, the PR number in tabular
grey; colour only as a second channel on the two words that carry state — failed (red) and
pending (ochre) — with ✓ ✕ ◷ ⊘ beside them so the state survives without colour. The data is the
design; chrome that does not say something about a repository is absent.

**Selection** — a repository is a card when, in the last 24 hours, one of its pull requests was
opened or merged, its head commit was committed (the `PROPOSES_COMMIT` join onto git_core's
commit, when that commit was observed), or a check on its head is still queued or running.
GitHub's `updated_at` — comments, labels, metadata edits — never qualifies. Reopen is not
observable on the collected node and is not counted.

**Order** — the organization's `criticality` custom property (`critical` > `high` > `medium` >
`low`), then most recent qualifying movement, then full name. A property that is unset, outside
the allowed values, or whose observability is `unobservable` renders the word *unclassified* with
the reason on hover — never blank, and the three causes stay distinguishable.

**Rows** — every open PR of a qualifying repository, number ascending, drafts marked. Per row:
the count of distinct passing checks, then failed-check names, then queued/running names, then
anything else (skipped, cancelled, neutral, an unknown word) compactly WITH its word. Distinct
means one result per (producing app, check name), keeping the highest `check_run_id`, so a rerun
replaces the run it re-ran and never counts beside it; two producers with the same check name stay
two checks. Results are the rollup of the PR's `head_sha` at collection; the collector replaces
head and checks together on every observation, so an old green cannot survive a new push.

**Three states** — `checks_observability = unobservable` reads *checks not observable*; an
observed head with no contexts reads *no checks reported*; neither is a count and neither is
green. A repository that qualified only by a merge reads *No open PRs · latest merge #n*.

**Collection line** — the newest github_core collection job: *collected N min ago* when the last
success is within 30 minutes; *(stale)* beyond it; *the latest attempt FAILED* when a failure
followed the last success; *no successful collection yet* when none has. The 30-minute threshold
is a placeholder until the cadence is declared where the panel can read it; the cadence itself is
an operational change outside this requirement. The coverage sentence on hover names what the
results are: GitHub check runs and commit statuses on the current head, which do not establish
approval, conflicts or merge readiness.

**Links** — repository name → github_core's repository page (`/samsite/repo?repository_entity_id=`);
PR number/title → GitHub; the passing count → the PR's checks tab; each failed or pending name →
that check's own URL. Text and symbols (✓ ✕ ◷ ⊘) carry state alongside colour.

#### Implementation

`tap_plugin/git_serious_double_tap/panels/demo_strip/__init__.py` — panel type
`double-tap-demo-strip` (registered in `apps.py`), reads through `execute_gryphon_raw` over four
declared queries (repositories, pull requests, the `PROPOSES_COMMIT` join, collection jobs) and
folds them in pure functions (`build_cards`, `dedupe_checks`, `classify_check`,
`collection_status`); template `templates/git_serious_double_tap/panels/demo_strip.html`; styles
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
| req-git-serious-double-tap-page-strip-6 | Live | Implemented | On the 8010 grid after a collection (2026-09-08): five cards, critical → high → unclassified, PR rows with passed counts and pending names, collection line fresh. | Observed by hand; a boot-and-test lane for this repo is #4. |

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
