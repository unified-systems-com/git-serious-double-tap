# git-serious double-tap

git-serious pointed at the organization that builds TAP. A **double-tap** plugin is one built to
introspect the TAP system and platform itself; this one holds only what is specific to the
unified-systems-com instance of git-serious — the pages and panels needed to work a running example
of our own CI/CD system.

## What this plugin owns

- The unified-systems-com pages: today `/double-tap`, which mounts three git-serious panels
  (status wall, not-observed workflows, the gates) by `USES_PANEL` edge and nothing else.
- The instance's choice of what to look at, in what arrangement.

## What lives elsewhere

- **git_serious** (`git-serious-tap`): the product — landing, org, workflow and gate pages, the
  panels and searches this plugin mounts, and the boot record this instance runs.
- **github_core** (`tap-plugin-github-core`): the GitHub vocabulary and collector.
- The rule: anything a second git-serious instance would also want is built there, not here.

## Scope

No models, edges, collectors or panel types. Manifest + GRIFT only. One install dependency,
`git-serious-tap`, because the GRIFT edges target entity ids git_serious seeds — so git_serious
must be installed and seeded before this plugin (boot-profile order).

## Read first

- `specs/spec-git-serious-double-tap-v0.md` — the plugin spec; one requirement per page.
- `tap_plugin/git_serious_double_tap/grift/home.grift.json` — the home page bundle.
- Core: `tap_plugins/specs/spec-tap-plugin-architecture.md`, `tap_grid/specs/spec-grift-v0.md`.

## The composition record

`tap_plugin/git_serious_double_tap/boot/git_serious_double_tap.boot.json` is the reproducible
instance profile: git-serious's closure at the same pins, then this plugin; seeds in that order;
fires the github_core collector against unified-systems-com; and **decides the landing page** —
`web.landing_entity_id` + `web.landing_slug` pin `/double-tap` by entity id (core
`req-web-page-landing`). Boot it from a core checkout with
`scripts/spawn-session.sh <label> --from <pointer>` (see `spec-tap-boot-bootstrap.md`). It needs a
core that carries the `web` section (tap#340); on an older core the record fails schema
validation, which is the right loud failure. No credential, path or local override is committed:
the `github_core:collector` secret is declared, never embedded.

## Install and validate

Add to a git-serious boot profile, after git_serious in both sections:

```json
{ "slug": "git_serious_double_tap", "enabled": true,
  "source": { "type": "editable", "path": "_dev-plugins/git_serious_double_tap" } }
{ "type": "seed-plugin", "plugin": "git_serious_double_tap", "enabled": true }
```

Then, in a core checkout: `uv run python -m tap.preboot --profile <profile>` (conformance,
reconciliation and dependency gates), `manage.py plugins` (the report), and `GET /double-tap`.
Structure-only validation with no Django: `python -m tap_plugins.validate_plugin tap_plugin/git_serious_double_tap`.
