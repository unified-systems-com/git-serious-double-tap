# git-serious double-tap Plugin Specification

## Plugin Identity

- **Slug:** `git_serious_double_tap` (dist `git-serious-double-tap-tap`, namespace `tap_plugin.git_serious_double_tap`)
- **Display name:** git-serious double-tap
- **Initial page route:** `/double-tap`
- **Initial panel types:** none of its own — v0 mounts git_serious's standard panels by edge
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
panel types, and any page a second git-serious instance would also want.

## Goals

| # | Name | Description |
| :---: | --- | --- |
| 1 | Instance configuration lives in a plugin | The unified-systems-com pages are a versioned, installable plugin, not hand edits on one grid. |
| 2 | Compose, never copy | Pages here mount product panels by `USES_PANEL` edge; no panel, search or template is duplicated from git_serious. |
| 3 | Push repeatable capability down | Anything a second instance would want is built in git_serious or github_core, then used from here. |
| 4 | Zero code | v0 ships a manifest and GRIFT only; the plugin proves the shape before it earns any Python. |

## Requirements

| RID | Name | Status | Notes |
| --- | --- | :---: | --- |
| req-git-serious-double-tap-scope | [Instance-Only Scope](#instance-only-scope) | Implemented | Manifest + GRIFT only; install dep on git_serious; no models, edges, collectors or panel types |
| req-git-serious-double-tap-page-home | [Home Page](#home-page) | Implemented | `/double-tap` mounts git-serious's status wall, not-observed and gates panels by edge |
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

Route `/double-tap`, nav weight 110 (after git-serious's own pages). The page mounts three panels
git_serious ships, by `USES_PANEL` edge whose target is the panel entity git_serious seeds:

| Slot | Panel (git_serious) | Question it answers |
| --- | --- | --- |
| `status-wall` | Status wall | Is anything broken right now, across every repository? |
| `not-observed` | Not observed in the collected window | Which workflows could we not say anything about? |
| `gates` | The gates | What gates each default branch, and what can we not see? |

The page carries no panel, search, projection or template of its own. It is the running example's
first screen and the place target-3 pages (map unified-systems) attach as they are found.

#### Implementation

`tap_plugin/git_serious_double_tap/grift/home.grift.json` — one batch: the page node and three
`USES_PANEL` edges. Panel targets: status wall `01a0632f-38b6-7440-9de9-3d5a3dadeb2a`, not-observed
`01a0632f-38b6-7440-9de9-3d5ba8eadfc4`, gates `01a067e1-8266-71e1-bb86-fba4947ee6a2` (from
git_serious's `landing.grift.json`; ids are stable across its re-publishes).

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-page-home-1 | Route Serves | Implemented | `GET /double-tap` on a booted git_serious instance with this plugin seeded returns 200 and renders the three slots. | |
| req-git-serious-double-tap-page-home-2 | Composition Only | Implemented | The bundle's only node is the page; its edges target git_serious-seeded panels, and the import reports no dangling edge when git_serious seeded first. | |

### v0 Non-Goals
----
RID: `req-git-serious-double-tap-nongoals`

Status: `Implemented`

- No models, edges, collectors or panel types — if one is needed, it is built in git_serious or
  github_core and used from here.
- No boot record of its own: the instance boots git-serious's record with this plugin added to
  the install and population sections.
- No second-instance generality: a page that any git-serious user would want is a git_serious page.

#### Acceptance Criteria

| ACID | Title | Status | Description | Notes |
| --- | --- | :---: | --- | --- |
| req-git-serious-double-tap-nongoals-1 | Stays Thin | Implemented | The runtime package contains no `models/`, `edges/`, `collectors/` or `templates/` directory. | Reviewed on every PR. |
