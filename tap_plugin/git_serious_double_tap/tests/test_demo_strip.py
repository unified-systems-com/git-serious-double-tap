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
    full_name: str,
    *,
    criticality: str | None = "high",
    observability: str = "observed",
    role: str = "plugin",
) -> dict[str, Any]:
    props: dict[str, Any] = {} if criticality is None else {"criticality": criticality}
    if role:
        props["repository-role"] = role
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


def test_card_links_to_the_git_serious_repository_page() -> None:
    card = build_cards(_env([_repo("o/r")], [_pr("o/r", 1)]), now=NOW)[0]
    assert card.page_url == "/git-serious/repository?repo=o/r"
    tap = build_cards(
        _env([_repo("unified-systems-com/tap")], [_pr("unified-systems-com/tap", 1)]),
        now=NOW,
    )[0]
    assert (
        tap.page_url == "/double-tap/tap"
    )  # the instance's own page for its own repository


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


# --- the workboard reading of a card --------------------------------------------


def test_card_state_and_nudge_precedence() -> None:
    repos = [_repo("o/f"), _repo("o/u"), _repo("o/p"), _repo("o/g"), _repo("o/q")]
    prs = [
        _pr(
            "o/f",
            1,
            checks=[
                _check("a", run_id=1),
                _check("rids", conclusion="failure", run_id=2),
                _check("gate", conclusion="", status="queued", run_id=3),
            ],
        ),
        _pr("o/u", 2, checks_observability="unobservable", checks=[]),
        _pr(
            "o/p",
            3,
            checks=[
                _check("a", run_id=1),
                _check("gate", conclusion="", status="in_progress", run_id=2),
            ],
        ),
        _pr("o/g", 4, checks=[_check("a", run_id=1), _check("b", run_id=2)]),
        _pr(
            "o/q",
            5,
            state="MERGED",
            created=timedelta(days=2),
            merged_at=_iso(timedelta(hours=1)),
        ),
    ]
    by = {c.full_name: c for c in build_cards(_env(repos, prs), now=NOW)}
    assert (by["o/f"].state, by["o/f"].headline) == (
        "failed",
        "Fix 1 failing check on PR #1",
    )
    assert by["o/f"].targets == [(1, "https://github.com/o/f/pull/1/checks")]
    assert (by["o/u"].state, by["o/u"].verb) == ("unobservable", "Look at")
    assert (by["o/p"].state, by["o/p"].headline) == (
        "pending",
        "Wait for 1 check on PR #3",
    )
    assert (by["o/g"].state, by["o/g"].headline) == ("green", "Review PR #4")
    assert by["o/g"].targets == [(4, "https://github.com/o/g/pull/4")]
    assert (by["o/q"].state, by["o/q"].headline) == (
        "quiet",
        "Nothing to do — latest merge PR #5",
    )


def test_board_summary_counts_in_board_order_without_zeros() -> None:
    from tap_plugin.git_serious_double_tap.panels.demo_strip import board_summary

    repos = [_repo("o/a"), _repo("o/b"), _repo("o/c")]
    prs = [
        _pr("o/a", 1, checks=[_check("x", conclusion="failure", run_id=1)]),
        _pr("o/b", 2, checks=[_check("x", conclusion="failure", run_id=1)]),
        _pr("o/c", 3, checks=[_check("x", run_id=1)]),
    ]
    summary = board_summary(build_cards(_env(repos, prs), now=NOW))
    assert [(s["state"], s["count"]) for s in summary] == [("failed", 2), ("green", 1)]


# --- the board --------------------------------------------------------------


def test_board_places_platform_products_plugins_and_support() -> None:
    from tap_plugin.git_serious_double_tap.panels.demo_strip import arrange_board

    gs, sam = (
        "unified-systems-com/git-serious-tap",
        "unified-systems-com/tap-plugin-samsite",
    )
    ghc = "unified-systems-com/tap-plugin-github-core"
    idc = "unified-systems-com/tap-plugin-identity-core"
    dt = "unified-systems-com/git-serious-double-tap"
    dev = "unified-systems-com/tap-dev-hooks"
    repos = [
        _repo("unified-systems-com/tap", criticality="critical", role="platform"),
        _repo(gs, role="product"),
        _repo(
            dt, role="product"
        ),  # role says product; the declared products row does not name it
        _repo(ghc, criticality="high"),
        _repo(idc, criticality="low"),
        _repo(dev, criticality="critical", role="support"),
    ]
    prs = [
        _pr("unified-systems-com/tap", 1, checks=[_check("a", run_id=1)]),
        _pr(gs, 2, checks=[_check("a", run_id=1)]),
        _pr(dt, 7, checks=[_check("a", run_id=1)]),
        _pr(ghc, 3, checks=[_check("a", run_id=1)]),
        _pr(idc, 4, checks=[_check("x", conclusion="failure", run_id=1)]),
        _pr(dev, 6, checks=[_check("a", run_id=1)]),
    ]
    board = arrange_board(build_cards(_env(repos, prs), now=NOW))
    assert board["platform"].full_name == "unified-systems-com/tap"
    assert [
        (p["label"], p["card"].full_name if p["card"] else None)
        for p in board["products"]
    ] == [("git-serious", gs), ("samsite", None)]
    # the plugins board: failed identity_core (low) before green github_core (high) before green double-tap (high, later name)
    assert [c.full_name for c in board["plugins"]] == [idc, dt, ghc]
    assert [c.full_name for c in board["support"]] == [dev]
    assert sam not in {c.full_name for c in board["plugins"]}


def test_product_card_carries_its_plugin_table_with_counts_and_red_lines() -> None:
    from tap_plugin.git_serious_double_tap.panels.demo_strip import (
        arrange_board,
        repo_index,
    )

    gs = "unified-systems-com/git-serious-tap"
    ghc = "unified-systems-com/tap-plugin-github-core"
    idc = "unified-systems-com/tap-plugin-identity-core"
    repos = [
        _repo("unified-systems-com/tap", criticality="critical", role="platform"),
        _repo(gs, role="product"),
        _repo(ghc, criticality="high"),
        _repo(idc, criticality="low"),
    ]
    prs = [
        _pr(ghc, 3, checks=[_check("a", run_id=1)]),
        _pr(
            ghc,
            8,
            checks=[
                _check("a", run_id=1),
                _check("gate", conclusion="", status="queued", run_id=2),
            ],
        ),
        _pr(idc, 4, checks=[_check("x", conclusion="failure", run_id=1)]),
    ]
    env = _env(repos, prs)
    board = arrange_board(build_cards(env, now=NOW), repo_index(env))
    gs_col = next(p for p in board["products"] if p["full_name"] == gs)
    assert (
        gs_col["card"] is not None and gs_col["card"].state == "quiet"
    )  # git-serious did not move but keeps its card
    table = {row["name"]: row for row in gs_col["plugins"]}
    assert table["tap-plugin-github-core"]["open"] == 2
    assert (
        table["tap-plugin-github-core"]["passing"],
        table["tap-plugin-github-core"]["waiting"],
        table["tap-plugin-github-core"]["failing"],
    ) == (1, 1, 0)
    assert table["tap-plugin-identity-core"]["failing"] == 1
    assert (
        table["git-core-tap"]["on_grid"] is False and table["git-core-tap"]["open"] == 0
    )
    assert [row["name"] for row in gs_col["plugins"]][:2] == [
        "git-core-tap",
        "tap-plugin-administrivia",
    ]  # record order
