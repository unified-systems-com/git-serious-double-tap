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
 *      workflow takes the lane of the first local workflow it calls.
 *   2. Lanes as containers. Synthetic lane nodes sit between the repository and its
 *      workflows (repository ⊃ lane ⊃ workflow), then `projectNested` runs again with the
 *      base configuration plus the lane level. Lanes stack in the pipelines column in the
 *      cardinal order (gate on top, then publish, scheduled, fleet, baseline); sources stay
 *      on the right and outputs on the left because the repository's ranked layout is the
 *      base's own. (Publish beside the gate rather than beneath it is the next cut — it
 *      needs a two-column lane row the natural layouts do not offer yet.)
 *   3. Cross-lane relationships the base picture cannot draw: `uses:` of a local reusable
 *      workflow and `workflow_run` chaining, as synthetic dashed / dotted edges.
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
    lane: "_tap_lane",
};
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
    [T.lane]: {width: 240, height: 60},
};
const DEFAULTS = {flow: "rtl", column_gap: 48, row_gap: 12};
// ---- end of the restated base ----------------------------------------------------------

//: Trigger precedence — the FIRST of these a workflow declares is its primary trigger.
const PRIMARY = ["pull_request", "pull_request_target", "merge_group", "push", "workflow_run", "schedule", "workflow_call", "workflow_dispatch"];

//: The five lanes in cardinal order, top to bottom inside the pipelines column.
const LANES = {
    gate: {order: 0, label: "PR gate — every change rolls through here"},
    publish: {order: 1, label: "Publish — images, release, tags"},
    scheduled: {order: 2, label: "Scheduled — on a clock, against main"},
    fleet: {order: 3, label: "Fleet — called from the plugin repositories"},
    baseline: {order: 4, label: "Reusable baseline — called by more than one lane"},
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
    for (const repo of repos) {
        const fullName = repo.data("_full_name") || repo.data("label") || "";
        const workflows = cy.nodes(`[entity_type = "${T.workflow}"]`).filter((n) => n.data("_viewport_parent") === repo.id());
        if (workflows.empty()) {
            warn("tap_lanes_no_workflows", `${fullName}: no workflows nested in the repository`);
            continue;
        }
        const facts = await _fetchWorkflowFacts(fullName, warn);
        const plan = _classify(workflows, facts, warn);
        _addLanes(cy, repo, plan);
        _drawRelationships(cy, plan);
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
            {name: "repository-has-lane", gryphon: `(parent:${T.repository})-[:${SYN.hasLane}]->(child:${T.lane})`},
            {name: "lane-holds-workflow", gryphon: `(parent:${T.lane})-[:${SYN.laneHolds}]->(child:${T.workflow})`},
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
            [T.lane]: {top: 10 + labelInset, right: 16, bottom: 12, left: 16},
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
            // The pipelines stage now holds the lanes, stacked top to bottom in cardinal order.
            [T.repository]: ranked("order", {columnLayout: "stack"}),
            // Inside a lane: one wide row of workflow boxes, first-fired toward the sources side.
            [T.lane]: ranked("order", {columnLayout: "flow", flowAspect: 3.2}),
            [T.workflow]: ranked("label"),
        },
    });
    warnings.push(...(result.warnings || []));
    placeParentLabels(cy, {anchor: "upper-left", inset: 8, parentFontSize: chrome.parentFontSize, parentFontWeight: chrome.parentFontWeight});
    settleStacks(cy);
    _style(cy);
    return {warnings};
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
            node: wf, id: wf.id(), path, name: f.name || wf.data("label") || _basename(path),
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
        item.lane = callee ? (callee.lane === "baseline" ? "fleet" : callee.lane) : "scheduled";
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
    for (const [key, lane] of Object.entries(LANES)) {
        if (!present.has(key)) continue;
        const id = `${T.lane}:${repo.id()}:${key}`;
        cy.add({
            group: "nodes",
            // `shape` is set because the base stylesheet maps it from data on every node.
            data: {id, entity_type: T.lane, label: lane.label, shape: "round-rectangle", _stage: STAGE.pipelines, _order: lane.order, _lane: key},
            classes: `tap-lane tap-lane-${key}`,
        });
        cy.add({group: "edges", data: {id: `${SYN.hasLane}:${id}`, source: repo.id(), target: id, edge_type: SYN.hasLane}, classes: "tap-lane-containment"});
        for (const item of plan.values()) {
            if (item.lane !== key) continue;
            cy.add({group: "edges", data: {id: `${SYN.laneHolds}:${item.id}`, source: id, target: item.id, edge_type: SYN.laneHolds}, classes: "tap-lane-containment"});
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
        .selector(`node[entity_type = "${T.lane}"]`)
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
        .selector(".tap-lane-calls")
        .style({"line-style": "dashed", "label": "data(label)"})
        .selector(".tap-lane-runs-after")
        .style({"line-style": "dotted", "label": "data(label)"})
        .update();
}

function _clear(cy) {
    cy.remove(cy.edges(".tap-lane-edge"));
    cy.remove(cy.edges(".tap-lane-containment"));
    cy.remove(cy.nodes(`[entity_type = "${T.lane}"]`));
}
