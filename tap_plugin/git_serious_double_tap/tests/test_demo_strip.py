"""The demo strip's folding rules, over fixture envelopes — no grid, no GitHub.

Covers req-git-serious-double-tap-page-strip: selection by qualifying movement, criticality
order, per-head check results with rerun dedupe, the three check-observability states, and the
collection line's four states.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from tap_plugin.git_serious_double_tap.panels.demo_strip import (
    UNCLASSIFIED,
    build_cards,
    classify_check,
    collection_status,
    dedupe_checks,
)

NOW = datetime(2026, 9, 9, 0, 0, tzinfo=UTC)


def _iso(delta: timedelta) -> str:
    return (NOW - delta).isoformat()


def _repo(
    full_name: str, *, criticality: str | None = "high", observability: str = "observed"
) -> dict[str, Any]:
    props = {} if criticality is None else {"criticality": criticality}
    return {
        "entity_id": f"repo-{full_name}",
        "entity_type": "github_core__github_repository",
        "data": {
            "full_name": full_name,
            "name": full_name.rsplit("/", 1)[-1],
            "html_url": f"https://github.com/{full_name}",
            "custom_properties": props,
            "custom_properties_observability": observability,
        },
    }


def _pr(
    full_name: str,
    number: int,
    *,
    state: str = "OPEN",
    created: timedelta = timedelta(hours=1),
    **extra: Any,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "full_name": full_name,
        "number": number,
        "title": f"PR {number}",
        "state": state,
        "is_draft": False,
        "head_sha": "a" * 40,
        "html_url": f"https://github.com/{full_name}/pull/{number}",
        "created_at": _iso(created),
        "merged_at": None,
        "checks_observability": "observed",
        "checks": [],
    }
    data.update(extra)
    return {
        "entity_id": f"pr-{full_name}-{number}",
        "entity_type": "github_core__pull_request",
        "data": data,
    }


def _check(
    name: str,
    *,
    conclusion: str = "success",
    status: str = "completed",
    app: str = "github-actions",
    run_id: int | None = None,
) -> dict[str, Any]:
    return {
        "kind": "check_run",
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "app": app,
        "url": f"https://ci/{name}/{run_id}",
        "check_run_id": run_id,
    }


def _env(
    repos: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    heads: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "repositories": {"nodes": repos},
        "pull_requests": {"nodes": prs},
        "heads": heads or {"nodes": [], "edges": []},
        "collection_jobs": {"nodes": []},
    }


# --- selection ---------------------------------------------------------------


def test_repository_qualifies_by_opened_merged_or_head_commit_only() -> None:
    old = timedelta(days=3)
    repos = [
        _repo("o/opened"),
        _repo("o/merged"),
        _repo("o/pushed"),
        _repo("o/quiet"),
        _repo("o/commented"),
    ]
    pushed_pr = _pr("o/pushed", 1, created=old)
    prs = [
        _pr("o/opened", 1, created=timedelta(hours=2)),
        _pr(
            "o/merged",
            2,
            state="MERGED",
            created=old,
            merged_at=_iso(timedelta(hours=5)),
        ),
        pushed_pr,
        _pr("o/quiet", 3, created=old),
        # GitHub's updated_at moved (a comment) — must NOT count.
        _pr("o/commented", 4, created=old, updated_at=_iso(timedelta(minutes=5))),
    ]
    heads = {
        "nodes": [
            {
                "entity_id": "c1",
                "entity_type": "git_core__git_commit",
                "data": {"committed_date": _iso(timedelta(hours=1))},
            }
        ],
        "edges": [
            {
                "data": {
                    "edge_type": "PROPOSES_COMMIT__github_core",
                    "from_entity_id": pushed_pr["entity_id"],
                    "to_entity_id": "c1",
                }
            }
        ],
    }
    names = [c.full_name for c in build_cards(_env(repos, prs, heads), now=NOW)]
    assert set(names) == {"o/opened", "o/merged", "o/pushed"}


def test_running_check_counts_as_movement_now() -> None:
    repos = [_repo("o/building")]
    prs = [
        _pr(
            "o/building",
            9,
            created=timedelta(days=9),
            checks=[_check("gate", conclusion="", status="in_progress", run_id=1)],
        )
    ]
    cards = build_cards(_env(repos, prs), now=NOW)
    assert [c.full_name for c in cards] == ["o/building"]
    assert [r.name for r in cards[0].rows[0].pending] == ["gate"]


def test_merged_only_repository_shows_latest_merge_and_no_rows() -> None:
    repos = [_repo("o/r")]
    prs = [
        _pr(
            "o/r",
            5,
            state="MERGED",
            created=timedelta(days=2),
            merged_at=_iso(timedelta(hours=3)),
        ),
        _pr(
            "o/r",
            7,
            state="MERGED",
            created=timedelta(days=2),
            merged_at=_iso(timedelta(hours=1)),
        ),
    ]
    card = build_cards(_env(repos, prs), now=NOW)[0]
    assert card.rows == []
    assert card.latest_merge_number == 7


def test_pull_request_without_a_repository_node_is_not_a_card() -> None:
    assert build_cards(_env([], [_pr("o/ghost", 1)]), now=NOW) == []


# --- order -------------------------------------------------------------------


def test_criticality_orders_then_recency_then_name() -> None:
    repos = [
        _repo("o/low-new", criticality="low"),
        _repo("o/crit-old", criticality="critical"),
        _repo("o/unset", criticality=None),
        _repo("o/unobs", criticality="critical", observability="unobservable"),
        _repo("o/high-b", criticality="high"),
        _repo("o/high-a", criticality="high"),
    ]
    prs = [
        _pr("o/low-new", 1, created=timedelta(minutes=1)),
        _pr("o/crit-old", 1, created=timedelta(hours=20)),
        _pr("o/unset", 1, created=timedelta(hours=2)),
        _pr("o/unobs", 1, created=timedelta(hours=2)),
        _pr("o/high-b", 1, created=timedelta(hours=4)),
        _pr("o/high-a", 1, created=timedelta(hours=4)),
    ]
    cards = build_cards(_env(repos, prs), now=NOW)
    assert [c.full_name for c in cards] == [
        "o/crit-old",
        "o/high-a",
        "o/high-b",
        "o/low-new",
        "o/unobs",
        "o/unset",
    ]
    by_name = {c.full_name: c for c in cards}
    assert by_name["o/unobs"].criticality == UNCLASSIFIED
    assert "not observable" in by_name["o/unobs"].criticality_note
    assert by_name["o/unset"].criticality_note == "criticality not set"


# --- rows and checks ---------------------------------------------------------


def test_rows_are_every_open_pr_by_number_with_drafts_marked() -> None:
    repos = [_repo("o/r")]
    prs = [
        _pr(
            "o/r", 12, created=timedelta(days=30)
        ),  # old but open: shown once the repo qualifies
        _pr("o/r", 3, created=timedelta(hours=1), is_draft=True),
        _pr("o/r", 8, state="CLOSED", created=timedelta(hours=1)),
    ]
    rows = build_cards(_env(repos, prs), now=NOW)[0].rows
    assert [(r.number, r.is_draft) for r in rows] == [(3, True), (12, False)]


def test_rerun_replaces_the_run_it_reran() -> None:
    entries = [
        _check("dco", conclusion="failure", run_id=10),
        _check("dco", conclusion="success", run_id=11),
        _check("gate", conclusion="success", run_id=12),
        _check(
            "gate", conclusion="success", run_id=12, app="other-app"
        ),  # same name, different producer: distinct
    ]
    deduped = dedupe_checks(entries)
    assert [(e["app"], e["name"], e["check_run_id"]) for e in deduped] == [
        ("github-actions", "dco", 11),
        ("github-actions", "gate", 12),
        ("other-app", "gate", 12),
    ]


def test_row_buckets_passed_failed_pending_other() -> None:
    repos = [_repo("o/r")]
    checks = [
        _check("a", run_id=1),
        _check("b", run_id=2),
        _check("rids", conclusion="failure", run_id=3),
        _check("gate", conclusion="", status="queued", run_id=4),
        _check("lint", conclusion="skipped", run_id=5),
        {
            "kind": "status",
            "name": "sonar",
            "status": "success",
            "conclusion": "",
            "app": "sonarcloud",
            "url": "https://s",
            "check_run_id": None,
        },
    ]
    row = build_cards(_env(repos, [_pr("o/r", 1, checks=checks)]), now=NOW)[0].rows[0]
    assert row.passed == 3
    assert [c.name for c in row.failed] == ["rids"]
    assert [c.name for c in row.pending] == ["gate"]
    assert [(c.name, c.detail) for c in row.other] == [("lint", "skipped")]


def test_check_observability_three_states_never_read_green() -> None:
    repos = [_repo("o/r")]
    prs = [
        _pr("o/r", 1, checks_observability="unobservable", checks=[]),
        _pr("o/r", 2, checks_observability="observed", checks=[]),
    ]
    rows = build_cards(_env(repos, prs), now=NOW)[0].rows
    assert rows[0].checks_state == "unobservable"
    assert rows[1].checks_state == "none"
    assert rows[0].passed == rows[1].passed == 0


def test_unknown_words_are_kept_not_dropped() -> None:
    result = classify_check({"name": "x", "status": "completed", "conclusion": "stale"})
    assert (result.bucket, result.detail) == ("other", "stale")


# --- collection line ---------------------------------------------------------


def _job(
    status: str, finished: timedelta, name: str = "GitHub Core Collector 2026"
) -> dict[str, Any]:
    return {
        "entity_id": name + status + str(finished),
        "data": {"name": name, "status": status, "finished_at": _iso(finished)},
    }


def test_collection_line_four_states() -> None:
    assert collection_status({"nodes": []}, now=NOW)["state"] == "never"
    assert (
        collection_status({"nodes": [_job("FAILED", timedelta(minutes=2))]}, now=NOW)[
            "state"
        ]
        == "never"
    )
    assert (
        collection_status(
            {"nodes": [_job("SUCCESSFUL", timedelta(minutes=2))]}, now=NOW
        )["state"]
        == "fresh"
    )
    assert (
        collection_status({"nodes": [_job("SUCCESSFUL", timedelta(hours=2))]}, now=NOW)[
            "state"
        ]
        == "stale"
    )
    failed_after = collection_status(
        {
            "nodes": [
                _job("SUCCESSFUL", timedelta(minutes=20)),
                _job("FAILED", timedelta(minutes=1)),
            ]
        },
        now=NOW,
    )
    assert failed_after["state"] == "failed"
    assert "FAILED" in failed_after["text"] and failed_after["last_success"] is not None


def test_collection_line_ignores_other_collectors() -> None:
    env = {
        "nodes": [
            _job("SUCCESSFUL", timedelta(minutes=1), name="AWS Core Collector 2026")
        ]
    }
    assert collection_status(env, now=NOW)["state"] == "never"
