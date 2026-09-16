"""The nightlies board's folding rules, over fixture envelopes — no grid, no GitHub.

Covers req-git-serious-double-tap-page-nightlies: which workflows are on the board, the latest
scheduled run per workflow, the five row states (failed / not observed / running / other /
green), the not-observed window, card and row order, and the summary line.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from tap_plugin.git_serious_double_tap.panels.nightlies import (
    STATE_ORDER,
    WINDOW,
    board_summary,
    build_cards,
    classify_run,
)

NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def _iso(delta: timedelta) -> str:
    return (NOW - delta).isoformat()


def _repo(full_name: str) -> dict[str, Any]:
    return {
        "entity_id": f"repo-{full_name}",
        "entity_type": "github_core__github_repository",
        "data": {
            "full_name": full_name,
            "name": full_name.rsplit("/", 1)[-1],
            "html_url": f"https://github.com/{full_name}",
        },
    }


def _workflow(full_name: str, name: str, *, triggers: list[str] | None = None) -> dict[str, Any]:
    return {
        "entity_id": f"wf-{full_name}-{name}",
        "entity_type": "github_core__github_workflow",
        "data": {
            "full_name": full_name,
            "name": name,
            "path": f".github/workflows/{name}.yml",
            "html_url": f"https://github.com/{full_name}/actions/workflows/{name}.yml",
            "configuration": {"triggers": ["schedule"] if triggers is None else triggers},
        },
    }


def _run(
    full_name: str,
    name: str,
    ident: str,
    *,
    ago: timedelta = timedelta(hours=2),
    conclusion: str = "success",
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "entity_id": f"run-{ident}",
        "entity_type": "github_core__github_actions_run",
        "data": {
            "full_name": full_name,
            "event": "schedule",
            "status": status,
            "conclusion": conclusion,
            "head_branch": "main",
            "run_started_at": _iso(ago),
            "html_url": f"https://github.com/{full_name}/actions/runs/{ident}",
        },
    }


def _edge(edge_type: str, src: str, dst: str) -> dict[str, Any]:
    return {"entity_id": f"edge-{src}-{dst}", "data": {"edge_type": edge_type, "from_entity_id": src, "to_entity_id": dst}}


def _env(
    repos: list[dict[str, Any]],
    workflows: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    *,
    run_of: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Wire DEFINES_WORKFLOW from each workflow's repo (its `full_name`) and EXECUTES_WORKFLOW per `run_of`."""
    defines = [_edge("DEFINES_WORKFLOW__github_core", f"repo-{w['data']['full_name']}", w["entity_id"]) for w in workflows]
    executes = [_edge("EXECUTES_WORKFLOW__github_core", run_id, wid) for run_id, wid in run_of.items()]
    return {
        "workflows": {"nodes": repos + workflows, "edges": defines},
        "runs": {"nodes": runs + workflows, "edges": executes},
        "collection_jobs": {"nodes": []},
    }


R = "unified-systems-com/tap-plugin-gryphon-playground"
T = "unified-systems-com/tap"


# --- classification -----------------------------------------------------------


def test_classify_run_five_states_and_unknown_words_kept() -> None:
    assert classify_run({"status": "completed", "conclusion": "success"}) == ("green", "success")
    assert classify_run({"status": "completed", "conclusion": "failure"}) == ("failed", "failure")
    assert classify_run({"status": "completed", "conclusion": "timed_out"}) == ("failed", "timed_out")
    assert classify_run({"status": "in_progress", "conclusion": ""}) == ("pending", "in_progress")
    assert classify_run({"status": "queued", "conclusion": None}) == ("pending", "queued")
    assert classify_run({"status": "completed", "conclusion": "cancelled"}) == ("other", "cancelled")
    assert classify_run({"status": "completed", "conclusion": "skipped"}) == ("other", "skipped")
    assert classify_run({}) == ("other", "unknown")


# --- selection ------------------------------------------------------------------


def test_only_scheduled_workflows_are_on_the_board() -> None:
    env = _env(
        [_repo(R)],
        [_workflow(R, "nightly"), _workflow(R, "ci", triggers=["push", "pull_request"])],
        [_run(R, "nightly", "1")],
        run_of={"run-1": f"wf-{R}-nightly"},
    )
    cards = build_cards(env, now=NOW)
    assert [c.full_name for c in cards] == [R]
    assert [r.name for r in cards[0].rows] == ["nightly"]


def test_a_workflow_with_scheduled_runs_but_no_declared_trigger_is_still_on_the_board() -> None:
    env = _env(
        [_repo(R)],
        [_workflow(R, "soak", triggers=["workflow_dispatch"])],
        [_run(R, "soak", "1")],
        run_of={"run-1": f"wf-{R}-soak"},
    )
    assert [r.name for r in build_cards(env, now=NOW)[0].rows] == ["soak"]


def test_a_workflow_whose_repository_is_not_on_the_grid_is_not_a_row() -> None:
    env = _env([], [_workflow(R, "nightly")], [_run(R, "nightly", "1")], run_of={"run-1": f"wf-{R}-nightly"})
    assert build_cards(env, now=NOW) == []


# --- latest run and the window -------------------------------------------------


def test_latest_scheduled_run_wins() -> None:
    env = _env(
        [_repo(R)],
        [_workflow(R, "nightly")],
        [
            _run(R, "nightly", "old", ago=timedelta(hours=20), conclusion="failure"),
            _run(R, "nightly", "new", ago=timedelta(hours=1), conclusion="success"),
        ],
        run_of={"run-old": f"wf-{R}-nightly", "run-new": f"wf-{R}-nightly"},
    )
    row = build_cards(env, now=NOW)[0].rows[0]
    assert row.state == "green"
    assert row.run_url.endswith("/runs/new")
    assert row.age == "1 h ago"


def test_declared_schedule_with_no_run_is_not_observed_never_green() -> None:
    env = _env([_repo(R)], [_workflow(R, "nightly")], [], run_of={})
    card = build_cards(env, now=NOW)[0]
    row = card.rows[0]
    assert (row.state, row.detail) == ("not_observed", "no scheduled run observed")
    assert row.run_url == "" and row.workflow_url.endswith("/nightly.yml")
    assert card.state == "not_observed"


def test_a_run_older_than_the_window_is_not_observed_and_says_what_was_last_seen() -> None:
    env = _env(
        [_repo(R)],
        [_workflow(R, "nightly")],
        [_run(R, "nightly", "1", ago=WINDOW + timedelta(hours=10), conclusion="failure")],
        run_of={"run-1": f"wf-{R}-nightly"},
    )
    row = build_cards(env, now=NOW)[0].rows[0]
    assert row.state == "not_observed"
    assert row.detail == "no scheduled run in the window; last observed failure 1 d ago"
    assert row.run_url.endswith("/runs/1")  # the old run stays reachable; only its verdict is not promoted


def test_window_is_configurable() -> None:
    env = _env(
        [_repo(R)],
        [_workflow(R, "nightly")],
        [_run(R, "nightly", "1", ago=timedelta(hours=30))],
        run_of={"run-1": f"wf-{R}-nightly"},
    )
    assert build_cards(env, now=NOW)[0].rows[0].state == "not_observed"
    assert build_cards(env, now=NOW, window=timedelta(hours=48))[0].rows[0].state == "green"


def test_running_and_other_states() -> None:
    env = _env(
        [_repo(R)],
        [_workflow(R, "a"), _workflow(R, "b")],
        [
            _run(R, "a", "1", ago=timedelta(minutes=5), conclusion="", status="in_progress"),
            _run(R, "b", "2", conclusion="cancelled"),
        ],
        run_of={"run-1": f"wf-{R}-a", "run-2": f"wf-{R}-b"},
    )
    rows = {r.name: r for r in build_cards(env, now=NOW)[0].rows}
    assert (rows["a"].state, rows["a"].detail) == ("pending", "in_progress")
    assert (rows["b"].state, rows["b"].detail) == ("other", "cancelled")


# --- order and summary ---------------------------------------------------------


def test_card_state_is_the_worst_row_and_cards_order_worst_first_then_name() -> None:
    env = _env(
        [_repo(T), _repo(R), _repo("unified-systems-com/zizmor-tap")],
        [_workflow(T, "api-fuzz-nightly"), _workflow(T, "grype-nightly"), _workflow(R, "nightly"), _workflow("unified-systems-com/zizmor-tap", "nightly")],
        [
            _run(T, "api-fuzz-nightly", "1", conclusion="success"),
            _run(T, "grype-nightly", "2", conclusion="failure"),
            _run("unified-systems-com/zizmor-tap", "nightly", "3", conclusion="success"),
        ],
        run_of={"run-1": f"wf-{T}-api-fuzz-nightly", "run-2": f"wf-{T}-grype-nightly", "run-3": "wf-unified-systems-com/zizmor-tap-nightly"},
    )
    cards = build_cards(env, now=NOW)
    assert [(c.name, c.state) for c in cards] == [("tap", "failed"), ("tap-plugin-gryphon-playground", "not_observed"), ("zizmor-tap", "green")]
    tap = cards[0]
    assert [(r.name, r.state) for r in tap.rows] == [("grype-nightly", "failed"), ("api-fuzz-nightly", "green")]
    assert tap.headline == "tap: 1 red, 1 green"
    assert board_summary(cards) == [
        {"state": "failed", "label": "red", "count": 1},
        {"state": "not_observed", "label": "not observed", "count": 1},
        {"state": "green", "label": "green", "count": 2},
    ]
    assert list(STATE_ORDER) == ["failed", "not_observed", "pending", "other", "green"]


def test_card_links_to_the_repository_page_with_the_tap_override() -> None:
    env = _env(
        [_repo(T), _repo(R)],
        [_workflow(T, "n"), _workflow(R, "n")],
        [_run(T, "n", "1"), _run(R, "n", "2")],
        run_of={"run-1": f"wf-{T}-n", "run-2": f"wf-{R}-n"},
    )
    urls = {c.name: c.page_url for c in build_cards(env, now=NOW)}
    assert urls["tap"] == "/double-tap/tap"
    assert urls["tap-plugin-gryphon-playground"] == "/git-serious/repository?repo=unified-systems-com%2Ftap-plugin-gryphon-playground"
