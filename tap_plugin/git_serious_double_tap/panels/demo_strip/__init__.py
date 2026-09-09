"""double-tap-demo-strip — one card per repository that moved in the last 24 hours, listing its open
pull requests with the check results of each PR's CURRENT head.

Spec: specs/spec-git-serious-double-tap-v0.md (req-git-serious-double-tap-page-strip).
Issue: unified-systems-com/git-serious-double-tap#6.

This is the first card-level panel in the system and it lives HERE, in the instance plugin, on
purpose (ruled 2026-09-08): make it work against one real organization first, then lift the
repeatable part into tap_web. Everything instance-specific — the 24-hour window, the criticality
order taken from unified-systems-com's own custom property — is the reason it starts as
double-tap code and not as a git_serious panel.

Reads go through Gryphon (``execute_gryphon_raw``, gated on ``grid.read``); no github_core or
git_core Python is imported, so the manifest's ``depends_on`` stays empty — the queries name
those plugins' node types, which is a data dependency the boot record already orders.

Three states, never two:

- a pull request whose ``checks_observability`` is ``unobservable`` reads *checks not observable*,
  never "no checks" and never green;
- an observed head with no contexts reads *no checks reported*;
- a stale or failed collection is said on the strip, and the cards below it are labelled with the
  time they are true for, so an old green never reads as a current one.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from django.http import HttpRequest

    from tap_web.models import Panel

logger = logging.getLogger(__name__)

#: The fixed selection window (George, 2026-09-08: strip only, 24 hours, no selector yet).
WINDOW = timedelta(hours=24)

#: A collection older than this is called stale on the strip. Placeholder until the collector's
#: cadence is declared somewhere the panel can read it (the three-minute cadence is a separate
#: operational change — Codex brief, 2026-09-08).
STALE_AFTER = timedelta(minutes=30)

#: unified-systems-com's ``criticality`` custom property, best first. Anything else — unset,
#: unobservable, or a value outside the org's allowed set — is ``unclassified`` and sorts last.
CRITICALITY_RANK: dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}
UNCLASSIFIED = "unclassified"

#: Check-result vocabulary. GitHub check runs carry ``status`` + ``conclusion``; commit statuses
#: carry one ``state`` the collector folds into the same two keys. Anything not named here is
#: shown as "other" WITH its raw word, never silently dropped into a count.
_PASSED = frozenset({"success"})
_FAILED = frozenset(
    {"failure", "error", "timed_out", "action_required", "startup_failure"}
)
_PENDING = frozenset(
    {"queued", "in_progress", "pending", "waiting", "requested", "expected"}
)

#: The four git-serious views the strip navigates to (slugs git_serious seeds).
NAVIGATION: list[dict[str, str]] = [
    {
        "label": "Organization",
        "href": "/git-serious/org",
        "hint": "The account and its repositories",
    },
    {
        "label": "Repository machinery",
        "href": "/git-serious",
        "hint": "Workflows, refs and runners per repository",
    },
    {
        "label": "The gate",
        "href": "/git-serious/gate",
        "hint": "What must be true for a commit to land",
    },
    {
        "label": "Status wall",
        "href": "/double-tap/status-wall",
        "hint": "Every workflow's latest run, and the ones not observed — the drill-down",
    },
]

#: github_core's repository landing page and the page variable it resolves (panels/_common.py).
REPO_PAGE_SLUG = "/samsite/repo"
REPO_PAGE_VAR = "repository_entity_id"

# The declared reads. Node-only scans and one edge pattern, kept separate because the executor
# will not mix them in one query. The collection-job scan is the readiness signal: the newest
# github_core job's status and finish time are what "last successful collection" means.
QUERIES: dict[str, str] = {
    "repositories": "MATCH (r:github_core__github_repository) RETURN r",
    "pull_requests": "MATCH (p:github_core__pull_request) RETURN p",
    "heads": (
        "MATCH (p:github_core__pull_request)-[:PROPOSES_COMMIT__github_core]->(c:git_core__git_commit) "
        "RETURN p, c"
    ),
    "collection_jobs": "MATCH (j:collection_job) RETURN j",
}

#: The collector whose jobs the readiness line reads. Matched on the job name prefix because the
#: job node carries no collector slug in its data.
COLLECTOR_NAME_PREFIX = "GitHub Core Collector"


@dataclass(frozen=True)
class CheckResult:
    """One distinct check on a PR head after rerun dedupe."""

    name: str
    app: str
    bucket: str  # passed | failed | pending | other
    detail: str  # the raw conclusion/status word, for "other" and for hover text
    url: str


@dataclass
class PullRow:
    """One compact line on a card."""

    number: int
    title: str
    html_url: str
    is_draft: bool
    head_sha: str
    checks_state: str  # observed | unobservable | none
    passed: int = 0
    failed: list[CheckResult] = field(default_factory=list)
    pending: list[CheckResult] = field(default_factory=list)
    other: list[CheckResult] = field(default_factory=list)

    @property
    def checks_url(self) -> str:
        return f"{self.html_url}/checks" if self.html_url else ""


@dataclass
class Card:
    """One repository that qualified for the window."""

    entity_id: str
    full_name: str
    name: str
    html_url: str
    page_url: str
    criticality: str
    criticality_note: str
    last_activity: datetime | None
    rows: list[PullRow]
    latest_merge_number: int | None
    #: The workboard reading of the card — what the eye should land on, then what to do.
    state: str = "quiet"  # failed | unobservable | pending | green | quiet
    verb: str = ""  # Fix | Look at | Wait for | Review | (none)
    lead: str = (
        ""  # words between the verb and the PR links, e.g. "2 failing checks on"
    )
    targets: list[tuple[int, str]] = field(
        default_factory=list
    )  # (PR number, where the link goes)
    tail: str = ""  # words after the links, e.g. "— checks not observable"

    @property
    def headline(self) -> str:
        """The nudge as one plain sentence — for tests, tooltips and screen readers."""
        links = ", ".join(f"PR #{n}" for n, _ in self.targets)
        return " ".join(
            part for part in (self.verb, self.lead, links, self.tail) if part
        )


#: Board order of the card states, most actionable first — the legend order and the summary line.
STATE_ORDER: tuple[str, ...] = ("failed", "unobservable", "pending", "green", "quiet")

STATE_LABELS: dict[str, str] = {
    "failed": "to fix",
    "unobservable": "to look at",
    "pending": "waiting on checks",
    "green": "to review",
    "quiet": "nothing to do",
}


class DemoStripPanelType:
    """Repository cards for the last 24 hours, rendered by the panel's own template."""

    slug: ClassVar[str] = "double-tap-demo-strip"
    label: ClassVar[str] = "double-tap demo strip"
    view: ClassVar[str] = "git_serious_double_tap/panels/demo_strip.html"
    css: ClassVar[list[str]] = ["git_serious_double_tap/css/demo_strip.css"]
    js: ClassVar[list[str]] = []
    config_defaults: ClassVar[dict[str, Any]] = {}

    @classmethod
    def get_view_context(cls, panel: Panel, request: HttpRequest) -> dict[str, Any]:
        """Run the declared reads and fold them into cards; render the failure rather than a blank."""
        now = datetime.now(UTC)
        config = dict(cls.config_defaults)
        config.update(panel.config or {})
        refresh_seconds = _positive_int(config.get("refresh_seconds"))
        try:
            env = _fetch(QUERIES)
        except (
            Exception
        ):  # noqa: BLE001 — the panel renders its failure, never a blank frame
            logger.exception(
                "[6aa9] demo strip reads failed for panel %s", panel.entity_id
            )
            return {
                "strip_error": "Strip reads failed — see the server log ([6aa9]).",
                "cards": [],
                "collection": None,
                "navigation": NAVIGATION,
                "window_hours": int(WINDOW.total_seconds() // 3600),
                "refresh_seconds": refresh_seconds,
            }
        cards = build_cards(env, now=now)
        collection = collection_status(env.get("collection_jobs", {}), now=now)
        return {
            "strip_error": None,
            "cards": cards,
            "summary": board_summary(cards),
            "collection": collection,
            "navigation": NAVIGATION,
            "window_hours": int(WINDOW.total_seconds() // 3600),
            "refresh_seconds": refresh_seconds,
        }


def _positive_int(value: Any) -> int:
    """``config.refresh_seconds`` → seconds, or 0 (off) for anything that is not a positive number."""
    try:
        seconds = int(value)
    except TypeError, ValueError:
        return 0
    return seconds if seconds > 0 else 0


def _fetch(queries: dict[str, str]) -> dict[str, dict[str, Any]]:
    from tap_grid.gryphon.executor import execute_gryphon_raw

    return {
        key: execute_gryphon_raw(query, {}, layer="full")
        for key, query in queries.items()
    }


# ---------------------------------------------------------------------------
# Folding — pure functions over search envelopes, so the tests need no grid
# ---------------------------------------------------------------------------


def _data(node: dict[str, Any]) -> dict[str, Any]:
    return dict(node.get("data") or {})


def _parse_ts(value: Any) -> datetime | None:
    """ISO-8601 text (or a datetime) → aware UTC datetime; anything else is None (unobserved)."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _criticality(repo: dict[str, Any]) -> tuple[str, str]:
    """(value, note): the org's custom property, or ``unclassified`` and WHY."""
    observability = str(repo.get("custom_properties_observability") or "")
    if observability == "unobservable":
        return UNCLASSIFIED, "custom properties not observable"
    props = repo.get("custom_properties") or {}
    raw = props.get("criticality") if isinstance(props, dict) else None
    if raw is None or raw == "":
        return UNCLASSIFIED, "criticality not set"
    value = str(raw).lower()
    if value not in CRITICALITY_RANK:
        return UNCLASSIFIED, f"criticality {raw!r} is outside the allowed values"
    return value, ""


def classify_check(entry: dict[str, Any]) -> CheckResult:
    """One rollup context → its bucket. Unknown words land in ``other`` carrying the word."""
    status = str(entry.get("status") or "").lower()
    conclusion = str(entry.get("conclusion") or "").lower()
    name = str(entry.get("name") or "")
    app = str(entry.get("app") or "")
    url = str(entry.get("url") or "")
    if conclusion in _PASSED or (not conclusion and status in _PASSED):
        return CheckResult(name, app, "passed", conclusion or status, url)
    if conclusion in _FAILED or (not conclusion and status in _FAILED):
        return CheckResult(name, app, "failed", conclusion or status, url)
    if status in _PENDING or (status and status != "completed" and not conclusion):
        return CheckResult(name, app, "pending", status, url)
    return CheckResult(name, app, "other", conclusion or status or "unknown", url)


def dedupe_checks(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest result per distinct (app, name): the highest ``check_run_id`` wins, so a rerun replaces
    the run it re-ran instead of counting beside it. Entries without an id (commit statuses) keep
    the last one seen, which is the rollup's own order."""
    latest: dict[tuple[str, str], tuple[int, int, dict[str, Any]]] = {}
    for position, entry in enumerate(entries):
        key = (str(entry.get("app") or ""), str(entry.get("name") or ""))
        run_id = entry.get("check_run_id")
        rank = int(run_id) if isinstance(run_id, int) else -1
        current = latest.get(key)
        if current is None or (rank, position) >= (current[0], current[1]):
            latest[key] = (rank, position, entry)
    return [item[2] for item in sorted(latest.values(), key=lambda item: item[1])]


def _pull_row(pr: dict[str, Any]) -> PullRow:
    row = PullRow(
        number=int(pr.get("number") or 0),
        title=str(pr.get("title") or ""),
        html_url=str(pr.get("html_url") or ""),
        is_draft=bool(pr.get("is_draft")),
        head_sha=str(pr.get("head_sha") or ""),
        checks_state="observed",
    )
    if str(pr.get("checks_observability") or "") == "unobservable":
        row.checks_state = "unobservable"
        return row
    entries = pr.get("checks") or []
    if not isinstance(entries, list) or not entries:
        row.checks_state = "none"
        return row
    for entry in dedupe_checks([e for e in entries if isinstance(e, dict)]):
        result = classify_check(entry)
        if result.bucket == "passed":
            row.passed += 1
        elif result.bucket == "failed":
            row.failed.append(result)
        elif result.bucket == "pending":
            row.pending.append(result)
        else:
            row.other.append(result)
    return row


def _qualifying_moments(
    pr: dict[str, Any], head_committed: datetime | None, since: datetime
) -> list[datetime]:
    """The moments that count as movement: opened, merged, head pushed (when observed). A check
    still queued or running counts as movement NOW. GitHub's ``updated_at`` never counts.
    """
    moments = [
        m
        for m in (
            _parse_ts(pr.get("created_at")),
            _parse_ts(pr.get("merged_at")),
            head_committed,
        )
        if m
    ]
    if str(pr.get("state") or "") == "OPEN":
        entries = pr.get("checks") or []
        if isinstance(entries, list) and any(
            classify_check(e).bucket == "pending"
            for e in entries
            if isinstance(e, dict)
        ):
            moments.append(
                since + WINDOW
            )  # "now": running work is movement by definition
    return [m for m in moments if m >= since]


def build_cards(env: dict[str, dict[str, Any]], *, now: datetime) -> list[Card]:
    """Select the repositories that moved in the window and fold their PRs into cards."""
    since = now - WINDOW
    repos_by_name: dict[str, dict[str, Any]] = {}
    for node in env.get("repositories", {}).get("nodes", []):
        data = _data(node)
        data["entity_id"] = str(node.get("entity_id") or data.get("entity_id") or "")
        if data.get("full_name"):
            repos_by_name[str(data["full_name"])] = data

    head_dates: dict[str, datetime | None] = {}
    heads = env.get("heads", {})
    commits = {
        str(n.get("entity_id")): _data(n)
        for n in heads.get("nodes", [])
        if n.get("entity_type") == "git_core__git_commit"
    }
    for edge in heads.get("edges", []):
        edata = edge.get("data") or {}
        if edata.get("edge_type") != "PROPOSES_COMMIT__github_core":
            continue
        commit = commits.get(str(edata.get("to_entity_id")))
        if commit is not None:
            head_dates[str(edata.get("from_entity_id"))] = _parse_ts(
                commit.get("committed_date")
            )

    per_repo: dict[str, list[tuple[dict[str, Any], list[datetime]]]] = defaultdict(list)
    for node in env.get("pull_requests", {}).get("nodes", []):
        pr = _data(node)
        moments = _qualifying_moments(
            pr, head_dates.get(str(node.get("entity_id"))), since
        )
        per_repo[str(pr.get("full_name") or "")].append((pr, moments))

    cards: list[Card] = []
    for full_name, items in per_repo.items():
        repo = repos_by_name.get(full_name)
        if repo is None:
            continue  # a PR whose repository is not on the grid is not a card; the repo scan is authoritative
        qualifying = [m for _, moments in items for m in moments]
        if not qualifying:
            continue
        open_rows = sorted(
            (_pull_row(pr) for pr, _ in items if pr.get("state") == "OPEN"),
            key=lambda r: r.number,
        )
        merged = [
            pr
            for pr, _ in items
            if pr.get("state") == "MERGED"
            and (_parse_ts(pr.get("merged_at")) or since) >= since
        ]
        latest_merge = max((int(pr.get("number") or 0) for pr in merged), default=None)
        criticality, note = _criticality(repo)
        card = Card(
            entity_id=str(repo.get("entity_id") or ""),
            full_name=full_name,
            name=full_name.rsplit("/", 1)[
                -1
            ],  # the org is the whole strip; the card says the repository
            html_url=str(repo.get("html_url") or ""),
            page_url=f"{REPO_PAGE_SLUG}?{REPO_PAGE_VAR}={repo.get('entity_id') or ''}",
            criticality=criticality,
            criticality_note=note,
            last_activity=max(qualifying),
            rows=open_rows,
            latest_merge_number=latest_merge,
        )
        _summarize(card)
        cards.append(card)
    cards.sort(
        key=lambda c: (
            CRITICALITY_RANK.get(c.criticality, len(CRITICALITY_RANK)),
            -(c.last_activity.timestamp() if c.last_activity else 0.0),
            c.full_name,
        )
    )
    return cards


def _targets(
    rows: list[PullRow], *, checks: bool = False, limit: int = 4
) -> list[tuple[int, str]]:
    """(number, url) per PR the nudge points at — the PR itself, or its checks tab when the
    action is about checks. Capped so the line stays a line; the rows below list the rest.
    """
    return [(r.number, r.checks_url if checks else r.html_url) for r in rows[:limit]]


def _summarize(card: Card) -> None:
    """Fold a card's rows into ONE state, one verb and one headline — the nudge.

    Precedence is by what the reader has to do, worst first: something failed (fix it) >
    something cannot be seen (look at GitHub) > something is still running (wait) > everything
    observed is green (review or merge is the human's call — passing checks do not establish
    approval) > nothing open (rest). The headline names the PR numbers so the nudge is
    self-contained: the reader can act from the card alone.
    """
    failed = [r for r in card.rows if r.failed]
    unobs = [r for r in card.rows if r.checks_state == "unobservable"]
    pending = [r for r in card.rows if r.pending and not r.failed]
    green = [
        r
        for r in card.rows
        if r.checks_state == "observed" and r.passed and not r.failed and not r.pending
    ]
    if failed:
        n = sum(len(r.failed) for r in failed)
        card.state, card.verb = "failed", "Fix"
        card.lead, card.targets = (
            f"{n} failing check{'s' if n != 1 else ''} on",
            _targets(failed, checks=True),
        )
    elif unobs:
        card.state, card.verb = "unobservable", "Look at"
        card.targets, card.tail = (
            _targets(unobs),
            "on GitHub — its checks are not observable",
        )
    elif pending:
        n = sum(len(r.pending) for r in pending)
        card.state, card.verb = "pending", "Wait for"
        card.lead, card.targets = f"{n} check{'s' if n != 1 else ''} on", _targets(
            pending, checks=True
        )
    elif green:
        card.state, card.verb = "green", "Review"
        card.targets = _targets(green)
    elif card.rows:
        card.state, card.verb = "quiet", "Look at"
        card.targets, card.tail = _targets(card.rows), "— no checks have reported yet"
    else:
        card.state, card.verb = "quiet", ""
        if card.latest_merge_number:
            card.lead = "Nothing to do — latest merge"
            card.targets = [
                (
                    card.latest_merge_number,
                    f"{card.html_url}/pull/{card.latest_merge_number}",
                )
            ]
        else:
            card.lead = "Nothing to do"


def board_summary(cards: list[Card]) -> list[dict[str, Any]]:
    """The board's first line: how many cards sit in each state, in board order, zeros omitted."""
    counts = dict.fromkeys(STATE_ORDER, 0)
    for card in cards:
        counts[card.state] = counts.get(card.state, 0) + 1
    return [
        {"state": state, "count": counts[state], "label": STATE_LABELS[state]}
        for state in STATE_ORDER
        if counts[state]
    ]


def collection_status(jobs_env: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    """What the strip says about the data's freshness — three states, never two.

    Returns ``state`` in {``never``, ``fresh``, ``stale``, ``failed``} with the last success time,
    the last attempt's status and time, and the human sentence the template shows.
    """
    jobs = [
        _data(n)
        for n in jobs_env.get("nodes", [])
        if str(_data(n).get("name") or "").startswith(COLLECTOR_NAME_PREFIX)
    ]
    finished: list[tuple[dict[str, Any], datetime]] = []
    for job in jobs:
        moment = _parse_ts(job.get("finished_at"))
        if moment is not None:
            finished.append((job, moment))
    if not finished:
        return {
            "state": "never",
            "last_success": None,
            "last_attempt": None,
            "last_status": "",
            "text": "no collection observed",
        }
    finished.sort(key=lambda item: item[1])
    successes = [
        moment for job, moment in finished if str(job.get("status")) == "SUCCESSFUL"
    ]
    last_success = successes[-1] if successes else None
    last_job, last_attempt = finished[-1]
    last_status = str(last_job.get("status") or "")
    # Never-succeeded outranks failed: "no data yet" is the more important thing to say.
    if last_success is None:
        state = "never"
    elif last_status == "FAILED":
        state = "failed"
    elif now - last_success > STALE_AFTER:
        state = "stale"
    else:
        state = "fresh"
    if last_success is None:
        text = f"no successful collection yet — last attempt {last_status.lower()} {_age(last_attempt, now)}"
    else:
        text = f"collected {_age(last_success, now)}"
        if state == "failed":
            text += f"; the latest attempt FAILED {_age(last_attempt, now)}"
        elif state == "stale":
            text += " (stale)"
    return {
        "state": state,
        "last_success": last_success,
        "last_attempt": last_attempt,
        "last_status": last_status,
        "text": text,
    }


def _age(moment: datetime | None, now: datetime) -> str:
    if moment is None:
        return "at an unknown time"
    seconds = max(0, int((now - moment).total_seconds()))
    if seconds < 90:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86400} d ago"
