/**
 * double-tap tap lanes layout — the tap-specific reading of one repository's CI machinery,
 * drawn OVER github_core's machinery projection (spec-git-serious-double-tap-v0.md,
 * req-git-serious-double-tap-tap-projection; git-serious-double-tap#12).
 *
 * This module runs second at the tap elevation. machinery.js has already resolved the
 * nesting github.com ⊃ account ⊃ repository ⊃ workflow ⊃ job, stamped `_stage` / `_order`
 * on every node, ranked jobs over `needs:` and drawn the chrome. The nested-projection
 * runtime keeps containment as `_viewport_parent` data (there are no cytoscape compound
 * nodes) and sizes every container in ONE `projectNested` pass — so adding a container level
 * means re-running that pass with the level added, not moving boxes by hand. This module:
 *
 *   1. Lanes by WHAT STARTS IT. Every workflow is classified by its primary trigger
 *      (pull_request / merge_group > push > workflow_run > schedule > workflow_call >
 *      workflow_dispatch) into one of five lanes — gate, publish, scheduled, fleet,
 *      baseline. A workflow_call workflow whose callers span more than one lane is the
 *      reusable baseline; one called from a single lane (or from other repositories) is
 *      fleet. A workflow_run workflow inherits its upstream's lane. A dispatch-only
 *      workflow takes the lane of the first local workflow it calls, else fleet.
 *   2. Lanes as containers, arranged by the cardinal map (George's mock, 2026-09-09).
 *      Synthetic containers sit between the repository and its workflows and
 *      `projectNested` runs again with the base configuration plus those levels:
 *          repository ⊃ pipelines block ⊃ { top row ⊃ { publish lane, gate lane },
 *                                            scheduled lane, fleet lane, baseline lane }
 *      The top row is a ranked layout so publish sits to the LEFT of the gate (its stage is
 *      the outputs side); the block is tiered rows so the scheduled lane is one horizontal
 *      line under the top row, ordered by time of day with the time on each label, and the
 *      fleet and baseline lanes sit beneath it. Sources stay on the right and outputs on the
 *      left because the repository's ranked layout is the base's own. Jobs inside the
 *      publish lane's workflows read left to right (mirrored after the pass), the way the
 *      publish chain is read.
 *   3. Cross-lane relationships the base picture cannot draw: `uses:` of a local reusable
 *      workflow and `workflow_run` chaining, as synthetic dashed / dotted edges.
 *   4. Destinations. A registry the publish lane's workflows name in their files (the
 *      collector extracts domain names from each workflow) is drawn as an output box on the
 *      left — ghcr.io today — with a "pushes" edge from every workflow that names it. It is
 *      derived from the YAML, so it is on the board before the registry's contents can be
 *      listed (GitHub Packages is closed to App credentials; req-github-core-packages); the
 *      package nodes fill it in once a token is placed.
 *
 * Nothing here names tap. The lanes are derived from the collected workflow
 * configuration, so the same module reads any repository; only the page pins which one.
 *
 * KNOWN DUPLICATE (tap-plugin-github-core#91): the base nesting configuration below —
 * type and edge names, base sizes, paddings, inner layouts, relationships — restates what
 * machinery.js hands to `projectNested`. It must match machinery.js exactly until that
 * module exports it; every edit there means putting eyes on this block.
 *
 * Standard tap layout module: `export async function execute(context)`
 * (spec-viz-layouts.md, req-viz-layout-module-contract).
 */

import {projectNested} from "/static/tap_viz/js/runtime/nested-projection.js";
import {applyStandardChrome, placeParentLabels, parentLabelInset} from "/static/tap_viz/js/runtime/chrome.js";
import {settleStacks} from "/static/tap_viz/js/runtime/stack.js";

const GRYPHON_URL = "/api/v1/gryphon/execute";

// ---- Base configuration, restated (tap-plugin-github-core#91) ----------------------------
const T = {
    platform: "github_core__github_platform",
    account: "github_core__github_account",
    repository: "github_core__github_repository",
    gitRepository: "git_core__git_repository",
    workflow: "github_core__github_workflow",
    job: "github_core__workflow_job",
    ref: "git_core__git_ref",
    ruleset: "github_core__github_ruleset",
    environment: "github_core__github_environment",
    app: "github_core__github_app",
    runner: "github_core__github_runner",
    issuer: "identity_core__oidc_issuer",
    placeholder: "_machinery_placeholder",
    registry: "_tap_registry",
    pipelines: "_tap_pipelines",
    toprow: "_tap_toprow",
    lane: "_tap_lane",
};
//: One entity type per lane so the tiered rows can tell them apart (they are matched by type).
const LANE_TYPE = {
    gate: "_tap_lane_gate", publish: "_tap_lane_publish", scheduled: "_tap_lane_scheduled",
    fleet: "_tap_lane_fleet", baseline: "_tap_lane_baseline",
};
const LANE_TYPES = Object.values(LANE_TYPE);
const isLaneType = (t) => LANE_TYPES.includes(t);
const E = {
    hostsAccount: "HOSTS_ACCOUNT__github_core",
    ownsRepo: "OWNS_REPO__github_core",
    definesWorkflow: "DEFINES_WORKFLOW__github_core",
    definesJob: "DEFINES_JOB__github_core",
    hasEnvironment: "DECLARES_ENVIRONMENT__github_core",
    protects: "PROTECTS_REPOSITORY__github_core",
};
const SYN = {
    hostsThirdParty: "_MACHINERY_HOSTS_THIRD_PARTY",
    hasPlaceholder: "_MACHINERY_HAS_PLACEHOLDER",
    hasRef: "_MACHINERY_HAS_REF",
    hasOutput: "_TAP_HAS_OUTPUT",
    pushesTo: "_TAP_PUSHES_TO",
    hasBlock: "_TAP_HAS_BLOCK",
    hasLane: "_TAP_HAS_LANE",
    laneHolds: "_TAP_LANE_HOLDS_WORKFLOW",
    calls: "_TAP_CALLS_WORKFLOW",
    runsAfter: "_TAP_RUNS_AFTER",
};
const STAGE = {sources: 0, pipelines: 1, outputs: 2};
const BASE_SIZES = {
    [T.platform]: {width: 480, height: 200},
    [T.account]: {width: 320, height: 120},
    [T.repository]: {width: 320, height: 90},
    [T.workflow]: {width: 200, height: 40},
    [T.job]: {width: 150, height: 34},
    [T.ref]: {width: 150, height: 34},
    [T.ruleset]: {width: 170, height: 34},
    [T.environment]: {width: 150, height: 34},
    [T.app]: {width: 180, height: 40},
    [T.runner]: {width: 180, height: 40},
    [T.issuer]: {width: 200, height: 40},
    [T.placeholder]: {width: 190, height: 30},
    [T.registry]: {width: 190, height: 44},
    [T.pipelines]: {width: 240, height: 60},
    [T.toprow]: {width: 240, height: 60},
    ...Object.fromEntries(LANE_TYPES.map((t) => [t, {width: 240, height: 60}])),
};
const DEFAULTS = {flow: "rtl", column_gap: 48, row_gap: 12};
// ---- end of the restated base ----------------------------------------------------------

//: Registries a workflow file can name. Matched against the collector's extracted domain names,
//: publish lane only — a domain in a scanner's file is an input, not a destination.
const REGISTRY_RE = /^(ghcr\.io|docker\.io|index\.docker\.io|quay\.io|public\.ecr\.aws|[\w.-]+\.dkr\.ecr\.[\w-]+\.amazonaws\.com|[\w.-]+\.pkg\.dev|mcr\.microsoft\.com|registry\.npmjs\.org|upload\.pypi\.org)$/;

//: Trigger precedence — the FIRST of these a workflow declares is its primary trigger.
const PRIMARY = ["pull_request", "pull_request_target", "merge_group", "push", "workflow_run", "schedule", "workflow_call", "workflow_dispatch"];

//: The five lanes. `row` places a lane in the pipelines block (0 = the top row beside the gate);
//: `stage` orders the top row (rtl: the outputs side is the left, so publish is stage 2).
const LANES = {
    gate: {row: 0, stage: STAGE.pipelines, label: "PR gate — every change rolls through here"},
    publish: {row: 0, stage: STAGE.outputs, label: "Publish — images, release, tags"},
    scheduled: {row: 1, stage: STAGE.pipelines, label: "Scheduled — on a clock, against main (UTC)"},
    fleet: {row: 2, stage: STAGE.pipelines, label: "Fleet — called from the plugin repositories"},
    baseline: {row: 3, stage: STAGE.pipelines, label: "Reusable baseline — called by more than one lane"},
};

export async function execute(context) {
    const {cy, projection} = context;
    const warnings = [];
    const warn = (category, message) => {
        warnings.push({category, message});
        console.warn(`[tap-machinery] ${category}: ${message}`);
    };
    const repos = cy.nodes(`[entity_type = "${T.repository}"]`);
    if (repos.empty()) {
        warn("tap_lanes_no_repository", "the scene holds no github_repository node; nothing to lane");
        return {warnings};
    }
    _clear(cy);
    const cfg = _readConfig(projection);
    const direction = cfg.flow === "ltr" ? "ltr" : "rtl";
    let laned = 0;
    const plans = [];
    for (const repo of repos) {
        const fullName = repo.data("_full_name") || repo.data("label") || "";
        const workflows = cy.nodes(`[entity_type = "${T.workflow}"]`).filter((n) => n.data("_viewport_parent") === repo.id());
        if (workflows.empty()) {
            warn("tap_lanes_no_workflows", `${fullName}: no workflows nested in the repository`);
            continue;
        }
        const facts = await _fetchWorkflowFacts(fullName, warn);
        const plan = _classify(workflows, facts, warn);
        _stampSchedule(plan, warn);
        _addLanes(cy, repo, plan);
        _addRegistries(cy, repo, plan, fullName);
        _drawRelationships(cy, plan);
        plans.push(plan);
        laned += plan.size;
    }
    if (!laned) return {warnings};

    // Re-run the nesting with the lane level added. Same base numbers as machinery.js
    // (tap-plugin-github-core#91), repository → lane → workflow instead of repository → workflow.
    const chrome = applyStandardChrome(cy, {
        leafTypes: [T.job, T.ref, T.ruleset, T.environment, T.app, T.runner, T.issuer, T.workflow],
        leafMaxWidth: 170,
    });
    const labelInset = parentLabelInset(chrome);
    const ranked = (sort, extra = {}) => ({name: "ranked", direction, columnGap: cfg.column_gap, rowGap: cfg.row_gap, sort, ...extra});
    const result = await projectNested(cy, {
        relationships: [
            {name: "platform-hosts-account", gryphon: `(parent:${T.platform})-[:${E.hostsAccount}]->(child:${T.account})`},
            {name: "platform-hosts-third-party", gryphon: `(parent:${T.platform})-[:${SYN.hostsThirdParty}]->(child)`},
            {name: "account-owns-repository", gryphon: `(parent:${T.account})-[:${E.ownsRepo}]->(child:${T.repository})`},
            {name: "repository-has-block", gryphon: `(parent:${T.repository})-[:${SYN.hasBlock}]->(child:${T.pipelines})`},
            {name: "repository-has-output", gryphon: `(parent:${T.repository})-[:${SYN.hasOutput}]->(child:${T.registry})`},
            {name: "block-has-toprow", gryphon: `(parent:${T.pipelines})-[:${SYN.hasBlock}]->(child:${T.toprow})`},
            {name: "block-has-lane", gryphon: `(parent)-[:${SYN.hasLane}]->(child)`},
            {name: "lane-holds-workflow", gryphon: `(parent)-[:${SYN.laneHolds}]->(child:${T.workflow})`},
            {name: "repository-has-ref", gryphon: `(parent:${T.repository})-[:${SYN.hasRef}]->(child:${T.ref})`},
            {name: "repository-has-environment", gryphon: `(parent:${T.repository})-[:${E.hasEnvironment}]->(child:${T.environment})`},
            {name: "ruleset-protects-repository", gryphon: `(parent:${T.repository})<-[:${E.protects}]-(child:${T.ruleset})`},
            {name: "repository-has-placeholder", gryphon: `(parent:${T.repository})-[:${SYN.hasPlaceholder}]->(child:${T.placeholder})`},
            {name: "workflow-defines-job", gryphon: `(parent:${T.workflow})-[:${E.definesJob}]->(child:${T.job})`},
        ],
        baseSizes: BASE_SIZES,
        padding: 14,
        paddings: {
            [T.platform]: {top: 40 + labelInset, right: 40, bottom: 40, left: 40},
            [T.account]: {top: 24 + labelInset, right: 34, bottom: 34, left: 34},
            [T.repository]: {top: 18 + labelInset, right: 28, bottom: 28, left: 28},
            [T.pipelines]: {top: 6, right: 6, bottom: 6, left: 6},
            [T.toprow]: {top: 6, right: 6, bottom: 6, left: 6},
            ...Object.fromEntries(LANE_TYPES.map((t) => [t, {top: 10 + labelInset, right: 16, bottom: 12, left: 16}])),
            [T.workflow]: {top: 6 + labelInset, right: 14, bottom: 14, left: 14},
        },
        innerLayout: {
            name: "tiered-rows",
            rowGap: 48,
            itemGap: 18,
            tiers: [
                {name: "third-parties", entityTypes: [T.app, T.issuer, T.runner]},
                {name: "account", entityTypes: [T.account]},
            ],
        },
        innerLayouts: {
            [T.account]: {name: "flow", aspect: 2.0, gap: 24, sort: "area-desc"},
            // The repository: sources | the pipelines block | outputs, the base's own columns.
            [T.repository]: ranked("order", {columnLayout: "stack"}),
            // The block: the top row, then the scheduled line, then fleet, then the baseline.
            [T.pipelines]: {
                name: "tiered-rows", rowGap: 28, itemGap: 24,
                tiers: [
                    {name: "top", entityTypes: [T.toprow]},
                    {name: "scheduled", entityTypes: [LANE_TYPE.scheduled]},
                    {name: "fleet", entityTypes: [LANE_TYPE.fleet]},
                    {name: "baseline", entityTypes: [LANE_TYPE.baseline]},
                ],
            },
            // The top row: publish (outputs stage) to the left of the gate (pipelines stage).
            [T.toprow]: ranked("order", {columnLayout: "stack"}),
            // Inside a lane: workflow boxes in a row, first-fired toward the sources side.
            [LANE_TYPE.gate]: ranked("order", {columnLayout: "flow", flowAspect: 3.2}),
            [LANE_TYPE.publish]: ranked("order", {columnLayout: "flow", flowAspect: 2.2}),
            [LANE_TYPE.fleet]: ranked("order", {columnLayout: "flow", flowAspect: 3.2}),
            [LANE_TYPE.baseline]: ranked("order", {columnLayout: "flow", flowAspect: 3.2}),
            // The scheduled line: one row, by time of day.
            [LANE_TYPE.scheduled]: ranked("order", {columnLayout: "flow", flowAspect: 60}),
            [T.workflow]: ranked("label"),
        },
    });
    warnings.push(...(result.warnings || []));
    for (const plan of plans) _mirrorPublishJobs(cy, plan);
    placeParentLabels(cy, {anchor: "upper-left", inset: 8, parentFontSize: chrome.parentFontSize, parentFontWeight: chrome.parentFontWeight});
    settleStacks(cy);
    _style(cy);
    return {warnings};
}

// ---------------------------------------------------------------------------
// The scheduled line: time of day from the cron, on the label and in the order
// ---------------------------------------------------------------------------

const CRON_RE = /cron:[ \t]*["']?([^\s"']+)[ \t]+([^\s"']+)[ \t]+[^\s"']+[ \t]+[^\s"']+[ \t]+[^\s"']+/;

function _stampSchedule(plan, warn) {
    for (const item of plan.values()) {
        const base = item.node.data("_label_base") || item.node.data("label") || "";
        item.node.data("_label_base", base);
        if (item.lane !== "scheduled") continue;
        const raw = String((item.conf && item.conf.raw_yaml) || "");
        const m = raw.match(CRON_RE);
        if (!m) {
            warn("tap_lanes_no_cron", `${item.name}: scheduled lane but no cron found in the workflow file`);
            item.node.data("_order", 24 * 60);
            continue;
        }
        const minute = Number.parseInt(m[1], 10);
        const hour = Number.parseInt(m[2], 10);
        if (Number.isNaN(minute) || Number.isNaN(hour)) {
            warn("tap_lanes_cron_unparsed", `${item.name}: cron "${m[0]}" is not a fixed time of day`);
            item.node.data("_order", 24 * 60);
            continue;
        }
        const hh = String(hour).padStart(2, "0");
        const mm = String(minute).padStart(2, "0");
        item.node.data("_order", hour * 60 + minute);
        item.node.data("label", `${base} — ${hh}:${mm}`);
    }
}

// ---------------------------------------------------------------------------
// The publish lane reads left to right inside its workflows (the mock, 2026-09-09):
// mirror each workflow's jobs about the box centre after the nesting pass.
// ---------------------------------------------------------------------------

function _mirrorPublishJobs(cy, plan) {
    for (const item of plan.values()) {
        if (item.lane !== "publish") continue;
        const cx = item.node.position("x");
        cy.nodes(`[_viewport_parent = "${item.id}"]`).forEach((job) => {
            job.position({x: 2 * cx - job.position("x"), y: job.position("y")});
        });
    }
}

function _readConfig(projection) {
    const raw = (projection && projection.definition && projection.definition.machinery)
        || (projection && projection.machinery) || {};
    return {...DEFAULTS, ...raw};
}

// ---------------------------------------------------------------------------
// Facts — the workflow configuration is not on the cy node data
// ---------------------------------------------------------------------------

async function _fetchWorkflowFacts(fullName, warn) {
    const byId = new Map();
    try {
        const rows = await _gryphonRows(
            [
                `MATCH (w:${T.workflow})`,
                "WHERE w.data.full_name = $repo",
                "RETURN w.entity_id AS entity_id, w.data.path AS path, w.data.name AS name, w.data.configuration AS configuration",
            ],
            {repo: fullName},
        );
        rows.forEach((row) => {
            if (row && row.entity_id) byId.set(String(row.entity_id), row);
        });
    } catch (err) {
        warn("tap_lanes_facts", `${fullName}: ${err.message}`);
    }
    return byId;
}

async function _gryphonRows(queryLines, inputs) {
    const headers = {"Content-Type": "application/json"};
    const csrf = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (csrf) headers["X-CSRFToken"] = csrf[1];
    const res = await fetch(GRYPHON_URL, {
        method: "POST",
        credentials: "same-origin",
        headers,
        body: JSON.stringify({query: queryLines.join("\n"), inputs: inputs || {}, layer: "lite"}),
    });
    if (!res.ok) throw new Error(`Gryphon ${res.status}: ${(await res.text()).slice(0, 200)}`);
    const body = await res.json();
    const rows = body.rows || (body.results && body.results.rows) || [];
    return Array.isArray(rows) ? rows : [];
}

// ---------------------------------------------------------------------------
// Classification — what starts it, and who calls whom
// ---------------------------------------------------------------------------

function _basename(path) {
    const s = String(path || "");
    return s.slice(s.lastIndexOf("/") + 1);
}

function _classify(workflows, facts, warn) {
    const items = new Map(); // id → item
    const byBasename = new Map();
    const byName = new Map();
    workflows.forEach((wf) => {
        const f = facts.get(wf.id()) || {};
        const conf = f.configuration || {};
        const path = f.path || "";
        const triggers = Array.isArray(conf.triggers) ? conf.triggers : [];
        const jobs = Array.isArray(conf.jobs) ? conf.jobs : [];
        const uses = jobs.map((j) => String(j.uses || "")).filter(Boolean);
        const runsAfterRaw = conf.workflow_run;
        const runsAfter = Array.isArray(runsAfterRaw)
            ? runsAfterRaw.map(String)
            : runsAfterRaw && typeof runsAfterRaw === "object" && Array.isArray(runsAfterRaw.workflows)
                ? runsAfterRaw.workflows.map(String)
                : [];
        const item = {
            node: wf, id: wf.id(), path, name: f.name || wf.data("label") || _basename(path), conf,
            triggers, primary: PRIMARY.find((t) => triggers.includes(t)) || null,
            dynamic: !!wf.data("_dynamic") || String(path).startsWith("dynamic/"),
            uses, runsAfterNames: runsAfter, callsLocal: [], calledBy: [], runsAfter: [], lane: null,
        };
        items.set(wf.id(), item);
        if (path) byBasename.set(_basename(path), item);
        if (item.name) byName.set(String(item.name), item);
    });
    for (const item of items.values()) {
        for (const u of item.uses) {
            if (!u.startsWith("./")) continue;
            const callee = byBasename.get(_basename(u.split("@")[0]));
            if (callee && callee !== item) {
                item.callsLocal.push(callee);
                callee.calledBy.push(item);
            }
        }
        for (const upstream of item.runsAfterNames) {
            const up = byName.get(upstream) || byBasename.get(_basename(upstream));
            if (up && up !== item) item.runsAfter.push(up);
        }
    }
    // Pass 1: lanes that follow from the trigger alone.
    for (const item of items.values()) {
        if (item.dynamic) item.lane = "gate";
        else if (item.primary === "pull_request" || item.primary === "pull_request_target" || item.primary === "merge_group") item.lane = "gate";
        else if (item.primary === "push") item.lane = "publish";
        else if (item.primary === "schedule") item.lane = "scheduled";
    }
    // Pass 2: workflow_run inherits its upstream's lane.
    for (const item of items.values()) {
        if (item.lane || item.primary !== "workflow_run") continue;
        const up = item.runsAfter.find((u) => u.lane);
        item.lane = up ? up.lane : "gate";
        if (!up) warn("tap_lanes_run_after_unresolved", `${item.name}: workflow_run upstream not found; placed in the gate lane`);
    }
    // Pass 3: workflow_call — baseline when callers span lanes, otherwise fleet.
    for (const item of items.values()) {
        if (item.lane || item.primary !== "workflow_call") continue;
        const callerLanes = new Set(item.calledBy.map((c) => c.lane).filter(Boolean));
        item.lane = callerLanes.size >= 2 ? "baseline" : "fleet";
    }
    // Pass 4: dispatch-only takes the lane of the first local workflow it calls.
    for (const item of items.values()) {
        if (item.lane) continue;
        const callee = item.callsLocal.find((c) => c.lane);
        // A hand-fired workflow that calls nothing local is fleet work (all-plugins runs the
        // plugin repositories' CI by hand); it has no clock, so it is not scheduled.
        item.lane = callee ? (callee.lane === "baseline" ? "fleet" : callee.lane) : "fleet";
        if (!item.primary) warn("tap_lanes_no_trigger", `${item.name}: no trigger observed; placed in the ${item.lane} lane`);
    }
    // Settle baseline once every caller has a lane.
    for (const item of items.values()) {
        if (item.primary !== "workflow_call") continue;
        const callerLanes = new Set(item.calledBy.map((c) => c.lane).filter(Boolean));
        item.lane = callerLanes.size >= 2 ? "baseline" : "fleet";
    }
    return items;
}

// ---------------------------------------------------------------------------
// Lane containers + relationships (synthetic nodes and edges for the nesting pass)
// ---------------------------------------------------------------------------

function _addLanes(cy, repo, plan) {
    const present = new Set([...plan.values()].map((i) => i.lane));
    const blockId = `${T.pipelines}:${repo.id()}`;
    const rowId = `${T.toprow}:${repo.id()}`;
    // `shape` is set because the base stylesheet maps it from data on every node.
    cy.add({group: "nodes", data: {id: blockId, entity_type: T.pipelines, label: "", shape: "round-rectangle", _stage: STAGE.pipelines, _order: 0}, classes: "tap-frame"});
    cy.add({group: "edges", data: {id: `${SYN.hasBlock}:${blockId}`, source: repo.id(), target: blockId, edge_type: SYN.hasBlock}, classes: "tap-lane-containment"});
    let rowAdded = false;
    for (const [key, lane] of Object.entries(LANES)) {
        if (!present.has(key)) continue;
        const id = `${T.lane}:${repo.id()}:${key}`;
        cy.add({
            group: "nodes",
            data: {id, entity_type: LANE_TYPE[key], label: lane.label, shape: "round-rectangle", _stage: lane.stage, _order: lane.stage, _lane: key},
            classes: `tap-lane tap-lane-${key}`,
        });
        let parentId = blockId;
        if (lane.row === 0) {
            if (!rowAdded) {
                cy.add({group: "nodes", data: {id: rowId, entity_type: T.toprow, label: "", shape: "round-rectangle", _stage: STAGE.pipelines, _order: 0}, classes: "tap-frame"});
                cy.add({group: "edges", data: {id: `${SYN.hasBlock}:${rowId}`, source: blockId, target: rowId, edge_type: SYN.hasBlock}, classes: "tap-lane-containment"});
                rowAdded = true;
            }
            parentId = rowId;
        }
        cy.add({group: "edges", data: {id: `${SYN.hasLane}:${id}`, source: parentId, target: id, edge_type: SYN.hasLane}, classes: "tap-lane-containment"});
        for (const item of plan.values()) {
            if (item.lane !== key) continue;
            cy.add({group: "edges", data: {id: `${SYN.laneHolds}:${item.id}`, source: id, target: item.id, edge_type: SYN.laneHolds}, classes: "tap-lane-containment"});
        }
    }
}

function _addRegistries(cy, repo, plan, fullName) {
    const byDomain = new Map(); // domain → [items]
    for (const item of plan.values()) {
        if (item.lane !== "publish") continue;
        const refs = (item.conf && item.conf.refs && item.conf.refs.domain_names) || [];
        for (const d of refs) {
            const domain = String(d || "").toLowerCase();
            if (!REGISTRY_RE.test(domain)) continue;
            if (!byDomain.has(domain)) byDomain.set(domain, []);
            byDomain.get(domain).push(item);
        }
    }
    let order = -10;
    for (const [domain, items] of byDomain) {
        const id = `${T.registry}:${repo.id()}:${domain}`;
        const owner = fullName.includes("/") ? fullName.split("/")[0] : "";
        const repoName = fullName.includes("/") ? fullName.split("/")[1] : "";
        // ghcr.io packages live under the GitHub org; other registries get no link until collected.
        const navUrl = domain === "ghcr.io" && owner ? `https://github.com/orgs/${owner}/packages?repo_name=${encodeURIComponent(repoName)}` : "";
        cy.add({
            group: "nodes",
            data: {id, entity_type: T.registry, label: `${domain} · registry`, shape: "round-rectangle", _stage: STAGE.outputs, _order: order++, _registry: domain,
                   nav_url: navUrl, nav_external: !!navUrl, _pushed_by: items.map((i) => i.name).join(", ")},
            classes: "tap-registry",
        });
        cy.add({group: "edges", data: {id: `${SYN.hasOutput}:${id}`, source: repo.id(), target: id, edge_type: SYN.hasOutput}, classes: "tap-lane-containment"});
        for (const item of items) {
            cy.add({group: "edges", data: {id: `${SYN.pushesTo}:${item.id}:${domain}`, source: item.id, target: id, edge_type: SYN.pushesTo, label: "pushes"}, classes: "tap-lane-edge tap-lane-pushes"});
        }
    }
}

function _drawRelationships(cy, plan) {
    for (const item of plan.values()) {
        for (const callee of item.callsLocal) {
            cy.add({group: "edges", data: {id: `${SYN.calls}:${item.id}:${callee.id}`, source: item.id, target: callee.id, edge_type: SYN.calls, label: "uses"}, classes: "tap-lane-edge tap-lane-calls"});
        }
        for (const up of item.runsAfter) {
            cy.add({group: "edges", data: {id: `${SYN.runsAfter}:${up.id}:${item.id}`, source: up.id, target: item.id, edge_type: SYN.runsAfter, label: "workflow_run"}, classes: "tap-lane-edge tap-lane-runs-after"});
        }
    }
}

// ---------------------------------------------------------------------------
// Style and re-entry
// ---------------------------------------------------------------------------

function _style(cy) {
    cy.style()
        .selector(".tap-frame")
        .style({"background-opacity": 0, "border-width": 0, "label": "", "events": "no"})
        .selector(".tap-lane")
        .style({
            "shape": "round-rectangle", "background-color": "#0e6b64", "background-opacity": 0.05,
            "border-width": 1, "border-style": "dashed", "border-color": "#0e6b64",
            "color": "#0a4f4a", "font-size": "12px", "font-weight": 600,
        })
        .selector(".tap-lane-gate")
        .style({"border-style": "solid", "border-width": 2, "border-color": "#1b1d22", "background-color": "#1b1d22", "background-opacity": 0.04, "color": "#1b1d22"})
        .selector(".tap-lane-containment")
        .style({"display": "none"})
        .selector(".tap-lane-edge")
        .style({"curve-style": "unbundled-bezier", "width": 1.5, "line-color": "#0e6b64", "target-arrow-color": "#0e6b64", "target-arrow-shape": "triangle", "arrow-scale": 0.9, "font-size": "9px", "color": "#0a4f4a", "text-background-color": "#ffffff", "text-background-opacity": 0.8, "text-background-padding": "2px", "z-index": 100})
        .selector(".tap-registry")
        .style({"background-color": "#1b1d22", "background-opacity": 0.9, "border-width": 2, "border-color": "#1b1d22", "color": "#ffffff", "font-size": "11px", "font-weight": 600, "text-valign": "center", "text-halign": "center", "text-wrap": "ellipsis", "text-max-width": "170px"})
        .selector(".tap-lane-pushes")
        .style({"line-style": "solid", "width": 2, "label": "data(label)", "line-color": "#1b1d22", "target-arrow-color": "#1b1d22"})
        .selector(".tap-lane-calls")
        .style({"line-style": "dashed", "label": "data(label)"})
        .selector(".tap-lane-runs-after")
        .style({"line-style": "dotted", "label": "data(label)"})
        .update();
}

function _clear(cy) {
    cy.remove(cy.edges(".tap-lane-edge"));
    cy.remove(cy.edges(".tap-lane-containment"));
    cy.remove(cy.nodes(".tap-lane"));
    cy.remove(cy.nodes(".tap-frame"));
    cy.remove(cy.nodes(".tap-registry"));
    cy.nodes("[_label_base]").forEach((n) => n.data("label", n.data("_label_base")));
}
