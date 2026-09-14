"""double-tap-nightlies — one card per repository that runs on a schedule, each row a scheduled
workflow's LATEST run: red when it failed, and NOT OBSERVED when nothing ran in the window.

Spec: specs/spec-git-serious-double-tap-v0.md (req-git-serious-double-tap-page-nightlies).
Issues: unified-systems-com/tap#137 (the nightly fuzz campaign reds its run; this is where the
red is read), unified-systems-com/tap#440 (the not-observed state — a nightly that never fired
must not look green).

The operator's ruling (2026-09-14): a failed nightly is signalled by the red run and READ on the
double-tap landing page — the nerve centre — not by a bot-filed issue or a page nobody opens.
github_core already collects every workflow run in the organization (`github_actions_run`:
event, conclusion, start time), so this panel is a fold over data on the grid, nothing more.

Reads go through Gryphon (``execute_gryphon_raw``, gated on ``grid.read``); no github_core Python
is imported, so the manifest's ``depends_on`` stays empty.

Three states, never two — and here a fourth, because the question is "did it run":

- a scheduled run whose conclusion is a failure word reads *failed*, red;
- a workflow that declares a schedule but has no scheduled run in the window reads
  *not observed*, never green — and if its last observed run is older than the window, that
  run's verdict is said in the detail, not promoted to the card's current state;
- a run still in flight reads *running*; a conclusion outside the vocabulary (cancelled, skipped)
  reads *other* WITH its word, never silently green or silently dropped;
- the collection's freshness is said on the board, so the window is measured against the data's
  age as well as the clock.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import quote

from tap_plugin.git_serious_double_tap.panels.demo_strip import (
    REPO_PAGE_OVERRIDES,
    REPO_PAGE_SLUG,
    REPO_PAGE_VAR,
    _age,
    _data,
    _fetch,
    _parse_ts,
    _positive_int,
    collection_status,
)

if TYPE_CHECKING:
    from django.http import HttpRequest

    from tap_web.models import Panel

logger = logging.getLogger(__name__)

#: A nightly is due once a day. 26 hours forgives GitHub's own scheduling drift (it delays and
#: drops on-the-hour crons) without letting a missed night read as fine.
WINDOW = timedelta(hours=26)

#: Run-conclusion vocabulary (GitHub's `conclusion` on a completed run). Anything not named here
#: is shown as "other" WITH its word, never folded into a count.
_FAILED = frozenset({"failure", "timed_out", "action_required", "startup_failure"})
_PASSED = frozenset({"success"})
_PENDING_STATUS = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})

#: The trigger word github_core's workflow parser records for `on: schedule:`.
SCHEDULE_TRIGGER = "schedule"

#: Board order of row/card states, most actionable first — the summary line and the card order.
STATE_ORDER: tuple[str, ...] = ("failed", "not_observed", "pending", "other", "green")
STATE_RANK: dict[str, int] = {s: i for i, s in enumerate(STATE_ORDER)}
STATE_LABELS: dict[str, str] = {
    "failed": "red",
    "not_observed": "not observed",
    "pending": "running",
    "other": "other",
    "green": "green",
}
STATE_GLYPHS: dict[str, str] = {
    "failed": "✕",
    "not_observed": "?",
    "pending": "◷",
    "other": "⊘",
    "green": "✓",
}

QUERIES: dict[str, str] = {
    # Every scheduled run with the workflow it executed. The envelope carries both node kinds
    # and the EXECUTES_WORKFLOW edges between them.
    "runs": (
        "MATCH (r:github_core__github_actions_run)-[e:EXECUTES_WORKFLOW__github_core]->(w:github_core__github_workflow) "
        'WHERE r.data.event = "schedule" RETURN r, w'
    ),
    # Every workflow with its repository — the declared schedules come from the workflow node's
    # `configuration.triggers`; a declared nightly with no run is the not-observed case.
    "workflows": (
        "MATCH (repo:github_core__github_repository)-[e:DEFINES_WORKFLOW__github_core]->(w:github_core__github_workflow) "
        "RETURN repo, w"
    ),
    "collection_jobs": "MATCH (j:collection_job) RETURN j",
}


@dataclass
class NightlyRow:
    """One scheduled workflow on a card: its latest scheduled run, or the absence of one."""

    workflow_entity_id: str
    name: str
    workflow_url: str
    state: str  # failed | not_observed | pending | other | green
    detail: str  # the conclusion/status word, or why it is not observed
    run_url: str = ""
    ran_at: datetime | None = None
    age: str = ""
    head_branch: str = ""

    @property
    def glyph(self) -> str:
        return STATE_GLYPHS[self.state]

    @property
    def label(self) -> str:
        return STATE_LABELS[self.state]


@dataclass
class NightlyCard:
    """One repository with at least one scheduled workflow."""

    entity_id: str
    full_name: str
    name: str
    html_url: str
    page_url: str
    rows: list[NightlyRow] = field(default_factory=list)
    state: str = "green"

    @property
    def headline(self) -> str:
        """One plain sentence for tooltips, tests and screen readers."""
        counts = _count_states(self.rows)
        parts = [f"{n} {STATE_LABELS[s]}" for s in STATE_ORDER if (n := counts.get(s))]
        return f"{self.name}: " + ", ".join(parts) if parts else f"{self.name}: no scheduled workflows"


class NightliesPanelType:
    """Nightly cards for the organization, rendered by the panel's own template."""

    slug: ClassVar[str] = "double-tap-nightlies"
    label: ClassVar[str] = "double-tap nightlies"
    view: ClassVar[str] = "git_serious_double_tap/panels/nightlies.html"
    #: The strip's stylesheet carries the card system; this one adds only the nightly states.
    css: ClassVar[list[str]] = [
        "git_serious_double_tap/css/demo_strip.css",
        "git_serious_double_tap/css/nightlies.css",
    ]
    js: ClassVar[list[str]] = []
    config_defaults: ClassVar[dict[str, Any]] = {}

    @classmethod
    def get_view_context(cls, panel: Panel, request: HttpRequest) -> dict[str, Any]:
        """Run the declared reads and fold them into cards; render the failure rather than a blank."""
        now = datetime.now(UTC)
        config = dict(cls.config_defaults)
        config.update(panel.config or {})
        refresh_seconds = _positive_int(config.get("refresh_seconds"))
        window = _window(config.get("window_hours"))
        try:
            env = _fetch(QUERIES)
        except Exception:  # noqa: BLE001 — the panel renders its failure, never a blank frame
            logger.exception("[b71c] nightlies reads failed for panel %s", panel.entity_id)
            return {
                "board_error": "Nightlies reads failed — see the server log ([b71c]).",
                "cards": [],
                "summary": [],
                "collection": None,
                "window_hours": int(window.total_seconds() // 3600),
                "refresh_seconds": refresh_seconds,
            }
        cards = build_cards(env, now=now, window=window)
        return {
            "board_error": None,
            "cards": cards,
            "summary": board_summary(cards),
            "collection": collection_status(env.get("collection_jobs", {}), now=now),
            "window_hours": int(window.total_seconds() // 3600),
            "refresh_seconds": refresh_seconds,
        }


def _window(value: Any) -> timedelta:
    """``config.window_hours`` → the not-observed window; the default when absent or not positive."""
    try:
        hours = int(value)
    except TypeError, ValueError:
        return WINDOW
    return timedelta(hours=hours) if hours > 0 else WINDOW


# ---------------------------------------------------------------------------
# Folding — pure functions over search envelopes, so the tests need no grid
# ---------------------------------------------------------------------------


def classify_run(run: dict[str, Any]) -> tuple[str, str]:
    """A run's (state, detail) from its status + conclusion. Unknown words land in ``other``."""
    status = str(run.get("status") or "").lower()
    conclusion = str(run.get("conclusion") or "").lower()
    if conclusion in _FAILED:
        return "failed", conclusion
    if conclusion in _PASSED:
        return "green", conclusion
    if not conclusion and (status in _PENDING_STATUS or (status and status != "completed")):
        return "pending", status
    return "other", conclusion or status or "unknown"


def _page_url(full_name: str) -> str:
    override = REPO_PAGE_OVERRIDES.get(full_name)
    if override:
        return override
    return f"{REPO_PAGE_SLUG}?{REPO_PAGE_VAR}={quote(full_name, safe='')}"


def _declares_schedule(workflow: dict[str, Any]) -> bool:
    configuration = workflow.get("configuration") or {}
    triggers = configuration.get("triggers") if isinstance(configuration, dict) else None
    return isinstance(triggers, list) and SCHEDULE_TRIGGER in [str(t) for t in triggers]


def _edges(env_part: dict[str, Any], edge_type: str) -> list[tuple[str, str]]:
    """(from_entity_id, to_entity_id) for every edge of one type in an envelope."""
    out: list[tuple[str, str]] = []
    for edge in env_part.get("edges", []):
        edata = edge.get("data") or {}
        if edata.get("edge_type") == edge_type:
            out.append((str(edata.get("from_entity_id")), str(edata.get("to_entity_id"))))
    return out


def build_cards(
    env: dict[str, dict[str, Any]], *, now: datetime, window: timedelta = WINDOW
) -> list[NightlyCard]:
    """Fold scheduled runs + declared schedules into one card per repository, worst first."""
    since = now - window

    # Workflows and the repository that defines each, from the DEFINES_WORKFLOW envelope.
    workflows_env = env.get("workflows", {})
    repos: dict[str, dict[str, Any]] = {}
    workflows: dict[str, dict[str, Any]] = {}
    for node in workflows_env.get("nodes", []):
        data = _data(node)
        data["entity_id"] = str(node.get("entity_id") or data.get("entity_id") or "")
        if node.get("entity_type") == "github_core__github_repository":
            repos[data["entity_id"]] = data
        elif node.get("entity_type") == "github_core__github_workflow":
            workflows[data["entity_id"]] = data
    repo_of_workflow: dict[str, str] = {}
    for repo_id, workflow_id in _edges(workflows_env, "DEFINES_WORKFLOW__github_core"):
        repo_of_workflow[workflow_id] = repo_id

    # Scheduled runs, and the workflow each executed, from the EXECUTES_WORKFLOW envelope.
    runs_env = env.get("runs", {})
    runs: dict[str, dict[str, Any]] = {}
    for node in runs_env.get("nodes", []):
        data = _data(node)
        data["entity_id"] = str(node.get("entity_id") or data.get("entity_id") or "")
        if node.get("entity_type") == "github_core__github_actions_run":
            runs[data["entity_id"]] = data
        elif node.get("entity_type") == "github_core__github_workflow":
            workflows.setdefault(data["entity_id"], data)
    runs_by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run_id, workflow_id in _edges(runs_env, "EXECUTES_WORKFLOW__github_core"):
        run = runs.get(run_id)
        if run is not None:
            runs_by_workflow[workflow_id].append(run)

    # A workflow is on the board if it declares a schedule or has ever run on one.
    on_board = {wid for wid, w in workflows.items() if _declares_schedule(w)} | set(runs_by_workflow)

    rows_by_repo: dict[str, list[NightlyRow]] = defaultdict(list)
    for workflow_id in on_board:
        workflow = workflows.get(workflow_id)
        if workflow is None:
            continue
        repo_id = repo_of_workflow.get(workflow_id) or _repo_id_from_runs(runs_by_workflow.get(workflow_id, []), repos)
        if repo_id is None:
            continue  # a workflow whose repository is not on the grid is not a row; the repo scan is authoritative
        rows_by_repo[repo_id].append(_row(workflow, runs_by_workflow.get(workflow_id, []), since=since, now=now))

    cards: list[NightlyCard] = []
    for repo_id, rows in rows_by_repo.items():
        repo = repos.get(repo_id)
        if repo is None:
            continue
        full_name = str(repo.get("full_name") or "")
        rows.sort(key=lambda r: (STATE_RANK[r.state], r.name.lower()))
        card = NightlyCard(
            entity_id=repo_id,
            full_name=full_name,
            name=str(repo.get("name") or full_name.rsplit("/", 1)[-1]),
            html_url=str(repo.get("html_url") or ""),
            page_url=_page_url(full_name),
            rows=rows,
            state=min((r.state for r in rows), key=lambda s: STATE_RANK[s]),
        )
        cards.append(card)
    cards.sort(key=lambda c: (STATE_RANK[c.state], c.name.lower()))
    return cards


def _repo_id_from_runs(runs: list[dict[str, Any]], repos: dict[str, dict[str, Any]]) -> str | None:
    """Fallback when a workflow lacks a DEFINES_WORKFLOW edge: the run's `full_name` names the repo."""
    names = {str(r.get("full_name") or "") for r in runs} - {""}
    for repo_id, repo in repos.items():
        if str(repo.get("full_name") or "") in names:
            return repo_id
    return None


def _row(
    workflow: dict[str, Any], runs: list[dict[str, Any]], *, since: datetime, now: datetime
) -> NightlyRow:
    name = str(workflow.get("name") or workflow.get("path") or "workflow")
    workflow_url = str(workflow.get("html_url") or "")
    latest: dict[str, Any] | None = None
    latest_at: datetime | None = None
    for run in runs:
        moment = _parse_ts(run.get("run_started_at")) or _parse_ts(run.get("created_at"))
        if latest is None or (moment is not None and (latest_at is None or moment > latest_at)):
            latest, latest_at = run, moment
    if latest is None:
        return NightlyRow(
            workflow_entity_id=str(workflow.get("entity_id") or ""),
            name=name,
            workflow_url=workflow_url,
            state="not_observed",
            detail="no scheduled run observed",
        )
    state, word = classify_run(latest)
    row = NightlyRow(
        workflow_entity_id=str(workflow.get("entity_id") or ""),
        name=name,
        workflow_url=workflow_url,
        state=state,
        detail=word,
        run_url=str(latest.get("html_url") or ""),
        ran_at=latest_at,
        age=_age(latest_at, now),
        head_branch=str(latest.get("head_branch") or ""),
    )
    if latest_at is None or latest_at < since:
        # An old verdict is not a current one: the row is NOT OBSERVED for the window, and what
        # was last seen is said in the detail rather than promoted to the card's state.
        row.state = "not_observed"
        row.detail = f"no scheduled run in the window; last observed {word} {row.age}"
    return row


def _count_states(rows: list[NightlyRow]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.state] += 1
    return dict(counts)


def board_summary(cards: list[NightlyCard]) -> list[dict[str, Any]]:
    """Counts of WORKFLOWS by state in board order, zeros omitted — the overview before the detail."""
    counts = _count_states([row for card in cards for row in card.rows])
    return [
        {"state": state, "label": STATE_LABELS[state], "count": counts[state]}
        for state in STATE_ORDER
        if counts.get(state)
    ]
