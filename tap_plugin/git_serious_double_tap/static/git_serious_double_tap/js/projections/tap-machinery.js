/**
 * double-tap tap lanes layout — the tap-specific reading of one repository's CI machinery,
 * drawn OVER github_core's machinery projection (spec-git-serious-double-tap-v0.md,
 * req-git-serious-double-tap-tap-projection; git-serious-double-tap#12).
 *
 * This module runs second at the tap elevation: machinery.js has already nested
 * github.com ⊃ account ⊃ repository ⊃ workflow ⊃ job, placed sources on the right and
 * outputs on the left, stamped `_stage` / `_order` on nodes and ranked jobs over `needs:`.
 * Nothing here re-nests or re-ranks. It does three things on top:
 *
 *   1. Lanes by WHAT STARTS IT. Every workflow is classified by its primary trigger
 *      (pull_request / merge_group > push > workflow_run > schedule > workflow_call >
 *      workflow_dispatch) into one of five lanes — gate, publish, scheduled, fleet,
 *      baseline. A workflow_call workflow whose callers span more than one lane is the
 *      reusable baseline; one called from a single lane (or from other repositories)
 *      is fleet. A workflow_run workflow inherits its upstream's lane. A dispatch-only
 *      workflow takes the lane of the first local workflow it calls.
 *   2. The cardinal map (George, 2026-09-09): the PR gate front and centre, publish to
 *      its left (artifacts on the left), scheduled below, fleet and the baseline at the
 *      bottom, sources untouched on the right. Lanes are synthetic compound parents
 *      inside the repository box so each band carries its own label.
 *   3. Cross-lane relationships the base picture cannot draw: `uses:` of a local
 *      reusable workflow and `workflow_run` chaining, as synthetic dashed edges.
 *
 * Nothing here names tap. The lanes are derived from the collected workflow
 * configuration, so the same module reads any repository; only the page pins which one.
 *
 * Standard tap layout module: `export async function execute(context)`
 * (spec-viz-layouts.md, req-viz-layout-module-contract).
 */

import {placeParentLabels} from "/static/tap_viz/js/runtime/chrome.js";
import {VIEWPORT_PARENT_CLASS} from "/static/tap_viz/js/runtime/nested-projection.js";

const GRYPHON_URL = "/api/v1/gryphon/execute";

const T = {
    repository: "github_core__github_repository",
    workflow: "github_core__github_workflow",
    job: "github_core__workflow_job",
    lane: "_tap_lane",
};

const SYN = {calls: "_TAP_CALLS_WORKFLOW", runsAfter: "_TAP_RUNS_AFTER"};

//: Trigger precedence — the FIRST of these a workflow declares is its primary trigger.
const PRIMARY = ["pull_request", "pull_request_target", "merge_group", "push", "workflow_run", "schedule", "workflow_call", "workflow_dispatch"];

//: The five lanes, with where they sit. Rows top→bottom; within row 0 the gate is centre-right
//: and publish is to its left (flow rtl: sources on the right, outputs on the left).
const LANES = {
    gate: {label: "PR gate — every change rolls through here", row: 0, col: 1},
    publish: {label: "Publish — images, release, tags", row: 0, col: 0},
    scheduled: {label: "Scheduled — on a clock, against main", row: 1, col: 0},
    fleet: {label: "Fleet — called from the plugin repositories", row: 2, col: 0},
    baseline: {label: "Reusable baseline — called by more than one lane", row: 3, col: 0},
};
const LANE_ORDER = ["gate", "publish", "scheduled", "fleet", "baseline"];

const GAP = {lane: 36, box: 28, band: 30, sources: 48};
const LANE_PAD = {top: 34, right: 18, bottom: 16, left: 18};

export async function execute(context) {
    const {cy} = context;
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
    for (const repo of repos) {
        const fullName = repo.data("_full_name") || repo.data("label") || "";
        const workflows = repo.children(`[entity_type = "${T.workflow}"]`);
        if (workflows.empty()) {
            warn("tap_lanes_no_workflows", `${fullName}: no workflow boxes inside the repository`);
            continue;
        }
        const facts = await _fetchWorkflowFacts(fullName, warn);
        const plan = _classify(workflows, facts, warn);
        _drawRelationships(cy, plan);
        _laneParents(cy, repo, plan);
        _layoutLanes(cy, repo, plan);
        _reseatSourcesAndOutputs(cy, repo, workflows);
    }
    _style(cy);
    placeParentLabels(cy, {anchor: "upper-left", inset: 8});
    return {warnings};
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
    const items = new Map(); // id → {node, path, name, triggers, primary, lane, callsLocal:[], runsAfter:[]}
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
    // Local reusable calls: `uses: ./.github/workflows/<file>` — resolve by basename.
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
        if (item.dynamic) item.lane = "gate"; // CodeQL / Copilot: run on PRs, no file of their own
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
    // Re-check baseline after passes 2–4 settled the callers' lanes.
    for (const item of items.values()) {
        if (item.primary !== "workflow_call") continue;
        const callerLanes = new Set(item.calledBy.map((c) => c.lane).filter(Boolean));
        item.lane = callerLanes.size >= 2 ? "baseline" : "fleet";
    }
    return items;
}

// ---------------------------------------------------------------------------
// Relationships across lanes
// ---------------------------------------------------------------------------

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
// Lane parents and placement
// ---------------------------------------------------------------------------

function _laneParents(cy, repo, plan) {
    const present = new Set([...plan.values()].map((i) => i.lane));
    for (const key of LANE_ORDER) {
        if (!present.has(key)) continue;
        const id = `${T.lane}:${repo.id()}:${key}`;
        cy.add({group: "nodes", data: {id, entity_type: T.lane, label: LANES[key].label, parent: repo.id(), _lane: key}, classes: `tap-lane tap-lane-${key} ${VIEWPORT_PARENT_CLASS}`});
        for (const item of plan.values()) {
            if (item.lane === key) item.node.move({parent: id});
        }
    }
}

function _boxOf(node) {
    return node.boundingBox({includeLabels: false, includeOverlays: false});
}

function _shiftBox(node, dx, dy) {
    if (!dx && !dy) return;
    const leaves = node.isParent() ? node.descendants().filter((n) => !n.isParent()) : node;
    leaves.shift({x: dx, y: dy});
}

function _layoutLanes(cy, repo, plan) {
    // Anchor: where the pipelines block stood before we regroup it, so the lanes replace it
    // in place and machinery.js's sources/outputs need only a re-seat, not a re-layout.
    const boxes = [...plan.values()].map((i) => i.node);
    const before = cy.collection(boxes).boundingBox({includeLabels: false});
    const x0 = before.x1;
    const y0 = before.y1;
    const byLane = new Map(LANE_ORDER.map((k) => [k, []]));
    for (const item of plan.values()) byLane.get(item.lane).push(item);
    // Within a lane: first-fired on the RIGHT (flow rtl), so sort by primary-trigger precedence
    // then name, and lay out right-to-left.
    const rank = (item) => [item.primary ? PRIMARY.indexOf(item.primary) : PRIMARY.length, item.name];
    for (const list of byLane.values()) list.sort((a, b) => (rank(a) < rank(b) ? -1 : rank(a) > rank(b) ? 1 : 0));
    const laneSize = (list) => {
        let w = 0;
        let h = 0;
        list.forEach((item, i) => {
            const bb = _boxOf(item.node);
            w += bb.w + (i ? GAP.box : 0);
            h = Math.max(h, bb.h);
        });
        return {w: w + LANE_PAD.left + LANE_PAD.right, h: h + LANE_PAD.top + LANE_PAD.bottom};
    };
    const rows = new Map();
    for (const key of LANE_ORDER) {
        const list = byLane.get(key);
        if (!list.length) continue;
        const r = LANES[key].row;
        if (!rows.has(r)) rows.set(r, []);
        rows.get(r).push(key);
    }
    let y = y0;
    for (const r of [...rows.keys()].sort((a, b) => a - b)) {
        const keys = rows.get(r).sort((a, b) => LANES[a].col - LANES[b].col);
        const sizes = keys.map((k) => laneSize(byLane.get(k)));
        const rowH = Math.max(...sizes.map((s) => s.h));
        let x = x0;
        keys.forEach((k, idx) => {
            const list = byLane.get(k);
            const size = sizes[idx];
            // Place boxes right-to-left inside the lane: the first item ends at the lane's right edge.
            let right = x + size.w - LANE_PAD.right;
            for (const item of list) {
                const bb = _boxOf(item.node);
                const targetX1 = right - bb.w;
                const targetY1 = y + LANE_PAD.top + (rowH - LANE_PAD.top - LANE_PAD.bottom - bb.h) / 2;
                _shiftBox(item.node, targetX1 - bb.x1, targetY1 - bb.y1);
                right = targetX1 - GAP.box;
            }
            x += size.w + GAP.lane;
        });
        y += rowH + GAP.band;
    }
}

function _reseatSourcesAndOutputs(cy, repo, workflows) {
    // Everything else inside the repository box that machinery.js placed to the right of the old
    // pipelines block is a source (refs, rulesets, the branch deck); to the left, an output.
    const after = workflows.boundingBox({includeLabels: false});
    const centre = (after.x1 + after.x2) / 2;
    const others = repo.children().filter((n) => n.data("entity_type") !== T.workflow && n.data("entity_type") !== T.lane);
    const sources = others.filter((n) => n.position("x") >= centre);
    const outputs = others.filter((n) => n.position("x") < centre);
    if (sources.nonempty()) {
        const sb = sources.boundingBox({includeLabels: true});
        const want = after.x2 + GAP.sources;
        if (sb.x1 < want) sources.shift({x: want - sb.x1, y: 0});
        const dy = after.y1 - sb.y1;
        if (dy) sources.shift({x: 0, y: dy});
    }
    if (outputs.nonempty()) {
        const ob = outputs.boundingBox({includeLabels: true});
        const want = after.x1 - GAP.sources;
        if (ob.x2 > want) outputs.shift({x: want - ob.x2, y: 0});
        const dy = after.y1 - ob.y1;
        if (dy) outputs.shift({x: 0, y: dy});
    }
}

// ---------------------------------------------------------------------------
// Style and re-entry
// ---------------------------------------------------------------------------

function _style(cy) {
    cy.style()
        .selector(`node[entity_type = "${T.lane}"]`)
        .style({
            "shape": "round-rectangle", "background-color": "#0e6b64", "background-opacity": 0.04,
            "border-width": 1, "border-style": "dashed", "border-color": "#0e6b64",
            "padding": "16px", "color": "#0a4f4a", "font-size": "12px", "font-weight": 600,
            "text-valign": "top", "text-halign": "left", "z-index": 0,
        })
        .selector(".tap-lane-gate")
        .style({"border-style": "solid", "border-width": 2, "border-color": "#1b1d22", "background-color": "#1b1d22", "background-opacity": 0.035, "color": "#1b1d22"})
        .selector(".tap-lane-edge")
        .style({"curve-style": "unbundled-bezier", "width": 1.5, "line-color": "#0e6b64", "target-arrow-color": "#0e6b64", "target-arrow-shape": "triangle", "arrow-scale": 0.9, "font-size": "9px", "color": "#0a4f4a", "text-background-color": "#ffffff", "text-background-opacity": 0.8, "text-background-padding": "2px"})
        .selector(".tap-lane-calls")
        .style({"line-style": "dashed", "label": "data(label)"})
        .selector(".tap-lane-runs-after")
        .style({"line-style": "dotted", "label": "data(label)"})
        .update();
}

function _clear(cy) {
    // Re-entry on the same cy: give the workflows back to their repository, then drop our nodes/edges.
    cy.nodes(`[entity_type = "${T.lane}"]`).forEach((lane) => {
        const repoId = lane.data("parent");
        lane.children().forEach((c) => c.move({parent: repoId || null}));
    });
    cy.remove(cy.nodes(`[entity_type = "${T.lane}"]`));
    cy.remove(cy.edges(".tap-lane-edge"));
}
