#!/usr/bin/env python3
"""Snapshot the repo's real state into a single-file board.

    ./scripts/board.py                    # writes docs/board.html
    ./scripts/board.py --out /tmp/b.html  # somewhere else
    ./scripts/board.py --json             # the model, for eyeballing

Everything on the board is read at run time from GitHub issues, pull
requests, CI runs, the git branches, the acceptance walkthroughs in the
repo root, and the preview stacks actually running on this box. Nothing
is typed in, so re-running it is the whole refresh story.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOW = datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# Collecting
# --------------------------------------------------------------------------


def run(cmd: list[str], cwd: Path = REPO) -> str:
    """Run a command, returning '' rather than exploding when it can't."""
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout if out.returncode == 0 else ""


def gh_json(args: list[str]) -> list[dict]:
    raw = run(["gh", *args])
    try:
        return json.loads(raw) if raw.strip() else []
    except json.JSONDecodeError:
        return []


def collect_issues() -> list[dict]:
    return gh_json(
        [
            "issue", "list", "--state", "all", "--limit", "300",
            "--json", "number,title,state,labels,createdAt,updatedAt,closedAt,url,body",
        ]
    )


def collect_prs() -> list[dict]:
    return gh_json(
        [
            "pr", "list", "--state", "all", "--limit", "150",
            "--json", "number,title,state,headRefName,createdAt,mergedAt,url,isDraft,body",
        ]
    )


def collect_runs() -> dict[str, dict]:
    """Latest CI run per branch."""
    runs = gh_json(
        [
            "run", "list", "--limit", "100",
            "--json", "headBranch,status,conclusion,createdAt,url,workflowName",
        ]
    )
    latest: dict[str, dict] = {}
    for r in sorted(runs, key=lambda r: r.get("createdAt", "")):
        latest[r.get("headBranch", "")] = r
    return latest


def collect_branches() -> list[dict]:
    fmt = "%(refname:short)\t%(committerdate:iso8601)\t%(contents:subject)"
    out = run(["git", "for-each-ref", "--sort=-committerdate", f"--format={fmt}",
               "refs/heads"])
    branches = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            branches.append({"name": parts[0], "date": parts[1], "subject": parts[2]})
    return branches


def collect_stacks() -> list[dict]:
    """Preview stacks up on this box right now, with the URL to click."""
    out = run(["docker", "compose", "ls", "--format", "json"])
    try:
        entries = json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        entries = []
    host = (run(["hostname", "-I"]).split() or ["localhost"])[0]
    stacks = []
    for e in entries:
        name = e.get("Name", "")
        if not name.startswith("aura-"):
            continue
        ticket = name[len("aura-"):]
        stacks.append(
            {
                "ticket": ticket,
                "status": e.get("Status", ""),
                "url": f"http://{host}:{preview_port(ticket)}/aura",
            }
        )
    return sorted(stacks, key=lambda s: s["ticket"])


def collect_shipped() -> set[int]:
    """Issues a squash-merge on main already delivered — `... (#27)`.

    Merge-commit subjects carry a *PR* number, so they are skipped: only the
    trailing `(#n)` GitHub appends on squash counts as a ticket reference.
    """
    shipped = set()
    for subject in run(["git", "log", "origin/main", "--format=%s"]).splitlines():
        if subject.startswith("Merge "):
            continue
        m = re.search(r"\(#(\d+)\)\s*$", subject)
        if m:
            shipped.add(int(m.group(1)))
    return shipped


def preview_port(ticket: str) -> int:
    """Mirror scripts/preview.sh: a ticket's port is derived from its name."""
    digits = "".join(c for c in ticket if c.isdigit())
    if digits and 1 <= int(digits) <= 99:
        return 8000 + int(digits)
    checksum = run(["bash", "-c", f"printf '%s' {ticket!r} | cksum | cut -d' ' -f1"])
    try:
        return 8000 + (int(checksum.strip()) % 89) + 10
    except ValueError:
        return 8000


def count_tests() -> dict[str, int]:
    """Test functions on disk — the automation half of 'is it done'."""

    def defs(root: Path) -> int:
        total = 0
        for path in root.rglob("test_*.py"):
            total += len(re.findall(r"^\s*def test_", path.read_text(errors="ignore"), re.M))
        return total

    pure = defs(REPO / "tests") if (REPO / "tests").is_dir() else 0
    site = defs(REPO / "auraos") if (REPO / "auraos").is_dir() else 0
    e2e = 0
    spec_dir = REPO / "frontend"
    if spec_dir.is_dir():
        for path in spec_dir.rglob("*.spec.[tj]s"):
            if "node_modules" in path.parts:
                continue
            e2e += len(re.findall(r"\btest\s*\(", path.read_text(errors="ignore")))
    return {"pure": pure, "site": site, "e2e": e2e}


# --------------------------------------------------------------------------
# Acceptance walkthroughs — the manual-test paper trail
# --------------------------------------------------------------------------

QUESTION = re.compile(r"^#{3,4} ")
ANSWER = re.compile(r"^>\s*\S")


def walkthrough_tickets(filename: str, by_code: dict[str, dict]) -> list[dict]:
    """`to-questionnaire-t31-t32-acceptance.md` -> the T3.1 and T3.2 tickets.

    The filename is the reliable signal: a walkthrough body links plenty of
    other issues (follow-ups it spawned), and the first of those is rarely
    the ticket it is deciding.
    """
    slug = filename.removeprefix("to-questionnaire-").removesuffix("-acceptance.md")
    found = []
    for part in slug.split("-"):
        digits = "".join(c for c in part if c.isdigit())
        if not digits:
            continue
        # `t31` is T3.1 in a filename that cannot carry a dot.
        for code in (f"T{digits}", f"T{digits[0]}.{digits[1:]}"):
            if code in by_code and by_code[code] not in found:
                found.append(by_code[code])
                break
    return found


def collect_walkthroughs(issues: list[dict]) -> list[dict]:
    by_code = {}
    for i in issues:
        code = ticket_code(i["title"])
        if code:
            by_code[code] = i
    docs = []
    for path in sorted(REPO.glob("to-questionnaire-*.md")):
        lines = path.read_text(errors="ignore").splitlines()
        title = next((l[2:].strip() for l in lines if l.startswith("# ")), path.stem)

        asked = answered = 0
        in_question = False
        got_answer = False
        in_verdict = False
        verdict = ""
        for line in lines:
            if line.startswith("## "):
                in_verdict = line[3:].strip().lower().startswith("verdict")
            if QUESTION.match(line):
                if in_question:
                    asked += 1
                    answered += got_answer
                in_question, got_answer = True, False
            elif in_question and ANSWER.match(line):
                got_answer = True
                if in_verdict and not verdict:
                    verdict = line.lstrip("> ").strip()
        if in_question:
            asked += 1
            answered += got_answer

        tickets = walkthrough_tickets(path.name, by_code)
        docs.append(
            {
                "file": path.name,
                "title": title,
                "tickets": [
                    {"number": t["number"], "url": t["url"],
                     "code": ticket_code(t["title"]), "state": t["state"]}
                    for t in tickets
                ],
                "asked": asked,
                "answered": answered,
                "verdict": verdict,
                # The ticket closing is the real sign-off; a written verdict
                # counts too, for the walkthrough answered but not yet actioned.
                "signed_off": bool(tickets) and all(t["state"] == "CLOSED" for t in tickets)
                or bool(verdict),
                "ticket_open": any(t["state"] == "OPEN" for t in tickets),
            }
        )
    return docs


# --------------------------------------------------------------------------
# The model
# --------------------------------------------------------------------------

TICKET = re.compile(r"^(T[\d.]*\d[a-z]?)\s*[:—-]", re.I)
LINKS = re.compile(r"\b(?:closes|fixes|resolves|refs|part of)\s+#(\d+)", re.I)

LANES = [
    ("triage", "Needs triage", "Raw — nobody has decided what it is yet"),
    ("founder", "Awaiting a decision", "Blocked on the founder, not on code"),
    ("ready", "Ready for agent", "Fully specified, nothing started"),
    ("flight", "In flight", "Branch open, CI not green yet"),
    ("manual", "Needs manual test", "Green build, waiting on a human to click it"),
    ("done", "Done", "Closed"),
]


def ticket_code(title: str) -> str:
    """`T6.1a: Company identity ...` -> `T6.1a`. The suffix letter is part
    of the name the tickets are actually called by, so its case is kept."""
    m = TICKET.match(title.strip())
    if not m:
        return ""
    code = m.group(1)
    return "T" + code[1:].lower()


def build_model() -> dict:
    issues = collect_issues()
    prs = collect_prs()
    runs = collect_runs()
    shipped = collect_shipped()

    # Which PR is working which issue.
    pr_for_issue: dict[int, list[dict]] = {}
    for pr in prs:
        pr["ci"] = runs.get(pr.get("headRefName", ""), {})
        targets = {int(n) for n in LINKS.findall(pr.get("body") or "")}
        code = ticket_code(pr.get("title", ""))
        if code:
            targets |= {i["number"] for i in issues if ticket_code(i["title"]) == code}
        for n in targets:
            pr_for_issue.setdefault(n, []).append(pr)

    all_stacks = collect_stacks()
    stacks = {s["ticket"].lower(): s for s in all_stacks}

    cards, pinned = [], None
    for issue in issues:
        code = ticket_code(issue["title"])
        linked = pr_for_issue.get(issue["number"], [])
        open_prs = [p for p in linked if p["state"] == "OPEN"]
        merged = [p for p in linked if p.get("mergedAt")]
        labels = [l["name"] for l in issue["labels"]]

        on_main = issue["number"] in shipped

        if issue["state"] == "CLOSED":
            lane = "done"
        elif open_prs:
            ci = (open_prs[0].get("ci") or {}).get("conclusion")
            lane = "manual" if ci == "success" else "flight"
        elif on_main:
            # Merged, but nobody has closed the ticket — it is waiting on a human.
            lane = "manual"
        elif "needs-triage" in labels:
            lane = "triage"
        elif "ready-for-human" in labels:
            lane = "founder"
        else:
            lane = "ready"

        card = {
            "number": issue["number"],
            "code": code,
            "title": re.sub(r"^T[\d.]*\d[a-z]?\s*[:—-]\s*", "", issue["title"]),
            "url": issue["url"],
            "labels": labels,
            "lane": lane,
            "updated": issue["updatedAt"],
            "closed": issue.get("closedAt"),
            "prs": [
                {
                    "number": p["number"],
                    "url": p["url"],
                    "state": "merged" if p.get("mergedAt") else p["state"].lower(),
                    "branch": p.get("headRefName", ""),
                    "ci": (p.get("ci") or {}).get("conclusion")
                    or (p.get("ci") or {}).get("status"),
                }
                for p in linked
            ],
            "merged_prs": len(merged),
            "on_main": on_main,
            "stack": stacks.get(code.lower()),
        }
        if issue["title"].lower().startswith("spec:"):
            pinned = card
        else:
            cards.append(card)

    cards.sort(key=lambda c: (c["code"] == "", natural(c["code"]), -c["number"]))

    orphan_prs = [
        {
            "number": p["number"], "title": p["title"], "url": p["url"],
            "branch": p.get("headRefName", ""),
            "ci": (p.get("ci") or {}).get("conclusion") or (p.get("ci") or {}).get("status"),
        }
        for p in prs
        if p["state"] == "OPEN"
        and not any(p["number"] in [q["number"] for q in c["prs"]] for c in cards)
    ]

    return {
        "generated": NOW.isoformat(timespec="seconds"),
        "head": run(["git", "rev-parse", "--short", "HEAD"]).strip(),
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip(),
        "dirty": len(run(["git", "status", "--porcelain"]).strip().splitlines()),
        "pinned": pinned,
        "cards": cards,
        "orphan_prs": orphan_prs,
        "open_prs": [p for p in prs if p["state"] == "OPEN"],
        "branches": collect_branches(),
        "runs": runs,
        "stacks": all_stacks,
        "walkthroughs": collect_walkthroughs(issues),
        "tests": count_tests(),
        "offline": not issues,
        "live_url": live_url(),
    }


def live_url() -> str:
    """Where the always-current copy is served, when it is installed."""
    if not Path("/etc/systemd/system/aura-board.timer").exists():
        return ""
    import os

    host = (run(["hostname", "-I"]).split() or ["localhost"])[0]
    return f"http://{host}:{os.environ.get('AURA_BOARD_PORT', '8200')}/"


def natural(code: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", code))


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

CSS = """
:root {
  --paper:#f6f6f4; --surface:#fff; --surface-2:#eeeeeb; --line:#dcdcd7;
  --ink:#17191d; --ink-2:#565a63; --ink-3:#888d96;
  --accent:#b8332b; --good:#2c7a55; --warn:#96690c; --info:#35618f; --idle:#767c86;
  --shadow:0 1px 2px rgba(23,25,29,.06),0 1px 8px rgba(23,25,29,.04);
  --shadow-hi:0 3px 12px rgba(23,25,29,.10);
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --paper:#131417; --surface:#1a1c20; --surface-2:#22252a; --line:#2e323a;
  --ink:#e9e9e6; --ink-2:#a6abb4; --ink-3:#787e88;
  --accent:#e06053; --good:#54b382; --warn:#d5a441; --info:#74a7de; --idle:#8a909a;
  --shadow:0 1px 2px rgba(0,0,0,.4); --shadow-hi:0 4px 14px rgba(0,0,0,.55);
}}
:root[data-theme="dark"]{
  --paper:#131417; --surface:#1a1c20; --surface-2:#22252a; --line:#2e323a;
  --ink:#e9e9e6; --ink-2:#a6abb4; --ink-3:#787e88;
  --accent:#e06053; --good:#54b382; --warn:#d5a441; --info:#74a7de; --idle:#8a909a;
  --shadow:0 1px 2px rgba(0,0,0,.4); --shadow-hi:0 4px 14px rgba(0,0,0,.55);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  font-size:15px; line-height:1.5; -webkit-font-smoothing:antialiased;
}
.mono{font-family:ui-monospace,SFMono-Regular,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums}
a{color:inherit}
.wrap{max-width:1380px; margin:0 auto; padding:0 24px 72px}

/* masthead */
header.top{border-bottom:1px solid var(--line); background:var(--surface); margin-bottom:28px}
.top .wrap{padding-top:26px; padding-bottom:0; display:flex; flex-direction:column; gap:20px}
.brandline{display:flex; align-items:baseline; gap:14px; flex-wrap:wrap}
h1{font-size:26px; letter-spacing:-.02em; margin:0; font-weight:650}
.tally{width:9px;height:9px;border-radius:50%;background:var(--accent);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 18%,transparent); flex:none}
.sub{color:var(--ink-3); font-size:13px}
.stamp{margin-left:auto; text-align:right; color:var(--ink-3); font-size:12px; line-height:1.7}

.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:1px;
  background:var(--line); border:1px solid var(--line); border-bottom:0;
  border-radius:8px 8px 0 0; overflow:hidden}
.stat{background:var(--surface); padding:12px 14px 14px}
.stat .n{font-size:23px; font-weight:640; letter-spacing:-.02em; display:block}
.stat .k{font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--ink-3)}
.stat.is-accent .n{color:var(--accent)}
.stat.is-good .n{color:var(--good)}
.stat.is-warn .n{color:var(--warn)}

/* kanban */
h2{font-size:12px; text-transform:uppercase; letter-spacing:.1em; color:var(--ink-3);
  margin:38px 0 12px; font-weight:600}
.board{display:grid; grid-auto-flow:column; grid-auto-columns:minmax(232px,1fr);
  gap:12px; overflow-x:auto; padding-bottom:10px; align-items:start}
.lane{background:var(--surface-2); border:1px solid var(--line); border-radius:10px;
  display:flex; flex-direction:column; min-height:90px}
.lane-head{padding:11px 13px 10px; border-bottom:1px solid var(--line);
  position:sticky; top:0; background:var(--surface-2); border-radius:10px 10px 0 0; z-index:1}
.lane-head .row{display:flex; align-items:center; gap:8px}
.lane-name{font-size:12.5px; font-weight:640; letter-spacing:-.005em}
.lane-count{margin-left:auto; font-size:12px; color:var(--ink-3)}
.lane-note{font-size:11.5px; color:var(--ink-3); margin-top:3px; line-height:1.35}
.dot{width:7px;height:7px;border-radius:2px;flex:none}
/* One long lane must not set the height of the whole board — it scrolls
   inside itself so all six stay comparable and the panels stay in view. */
.lane-cards{display:flex; flex-direction:column; gap:8px; padding:10px;
  max-height:min(66vh,720px); overflow-y:auto}
.empty{padding:14px 13px; color:var(--ink-3); font-size:12.5px}

.card{background:var(--surface); border:1px solid var(--line); border-left-width:3px;
  border-radius:7px; padding:10px 11px; box-shadow:var(--shadow); text-decoration:none;
  display:block; transition:transform .09s ease, box-shadow .09s ease}
.card:hover{transform:translateY(-1px); box-shadow:var(--shadow-hi)}
.card:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
.card .id{font-size:11px; color:var(--ink-3); display:flex; gap:7px; align-items:center}
.code{color:var(--accent); font-weight:640}
.card .t{font-size:13.5px; line-height:1.35; margin-top:4px; text-wrap:balance}
.chips{display:flex; flex-wrap:wrap; gap:5px; margin-top:8px}
.chip{font-size:10.5px; padding:2px 6px; border-radius:4px; border:1px solid var(--line);
  color:var(--ink-2); background:var(--surface-2); letter-spacing:.01em}
.chip.pr{border-color:color-mix(in srgb,var(--info) 40%,var(--line)); color:var(--info)}
.chip.ok{border-color:color-mix(in srgb,var(--good) 40%,var(--line)); color:var(--good)}
.chip.bad{border-color:color-mix(in srgb,var(--accent) 40%,var(--line)); color:var(--accent)}
.chip.warn{border-color:color-mix(in srgb,var(--warn) 40%,var(--line)); color:var(--warn)}
.chip.live{border-color:color-mix(in srgb,var(--good) 45%,var(--line)); color:var(--good);
  background:color-mix(in srgb,var(--good) 8%,var(--surface))}

/* pinned spec */
.pinned{display:flex; gap:12px; align-items:flex-start; background:var(--surface);
  border:1px solid var(--line); border-radius:10px; padding:13px 15px; box-shadow:var(--shadow);
  text-decoration:none}
.pinned .t{font-size:14px; font-weight:600; display:block}
.pinned .d{font-size:12.5px; color:var(--ink-3); margin-top:2px; display:block}

/* panels */
/* Wide enough that the status column — the reason to read the table —
   fits without the panel scrolling sideways. */
.panels{display:grid; grid-template-columns:repeat(auto-fit,minmax(440px,1fr)); gap:20px}
.panel{background:var(--surface); border:1px solid var(--line); border-radius:10px;
  overflow:hidden; box-shadow:var(--shadow)}
.panel h3{margin:0; padding:12px 15px; font-size:12px; text-transform:uppercase;
  letter-spacing:.09em; color:var(--ink-2); border-bottom:1px solid var(--line);
  background:var(--surface-2); font-weight:640}
.panel .scroll{overflow-x:auto}
table{width:100%; border-collapse:collapse; font-size:12.5px}
th{text-align:left; font-weight:600; color:var(--ink-3); font-size:11px;
  text-transform:uppercase; letter-spacing:.06em; padding:8px 15px; border-bottom:1px solid var(--line)}
td{padding:9px 15px; border-bottom:1px solid var(--line); vertical-align:top}
tr:last-child td{border-bottom:0}
td.num{text-align:right; white-space:nowrap}
.muted{color:var(--ink-3)}
.trunc{max-width:min(340px,26vw); overflow:hidden; text-overflow:ellipsis; white-space:nowrap}

.meter{display:inline-block; width:52px; height:5px; border-radius:3px;
  background:var(--surface-2); border:1px solid var(--line); overflow:hidden;
  vertical-align:middle; margin-right:7px}
.meter i{display:block; height:100%; background:var(--good)}
.status{font-weight:600}
.status.ok{color:var(--good)} .status.bad{color:var(--accent)}
.status.warn{color:var(--warn)} .status.idle{color:var(--ink-3)}

footer{margin-top:40px; padding-top:16px; border-top:1px solid var(--line);
  color:var(--ink-3); font-size:12px; line-height:1.7}
code.cmd{background:var(--surface-2); border:1px solid var(--line); border-radius:4px;
  padding:1px 5px; font-family:ui-monospace,Menlo,monospace; font-size:11.5px; color:var(--ink-2)}
.banner{background:color-mix(in srgb,var(--warn) 12%,var(--surface));
  border:1px solid color-mix(in srgb,var(--warn) 40%,var(--line)); color:var(--warn);
  border-radius:8px; padding:10px 14px; font-size:13px; margin-bottom:20px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

LANE_COLOR = {
    "triage": "var(--idle)",
    "founder": "var(--warn)",
    "ready": "var(--info)",
    "flight": "var(--accent)",
    "manual": "var(--warn)",
    "done": "var(--good)",
}


def e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def ago(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    hours = (NOW - then).total_seconds() / 3600
    if hours < 1:
        return "just now"
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours // 24)}d ago"


def ci_class(conclusion: str | None) -> str:
    return {
        "success": "ok", "failure": "bad", "cancelled": "warn",
        "in_progress": "warn", "queued": "warn", "startup_failure": "bad",
    }.get(conclusion or "", "idle")


def render_card(c: dict) -> str:
    chips = []
    for pr in c["prs"]:
        if pr["state"] == "merged":
            chips.append(f'<span class="chip ok mono">#{pr["number"]} merged</span>')
        elif pr["state"] == "open":
            cls = ci_class(pr["ci"])
            label = {"ok": "CI green", "bad": "CI red", "warn": "CI running"}.get(cls, "no CI")
            chips.append(
                f'<span class="chip pr mono">PR #{pr["number"]}</span>'
                f'<span class="chip {cls}">{label}</span>'
            )
    if c["on_main"] and c["lane"] != "done":
        chips.append('<span class="chip ok">on main — close it?</span>')
    if c["stack"]:
        chips.append(
            f'<span class="chip live">preview up</span>'
        )
    for label in c["labels"]:
        if label not in ("enhancement",):
            chips.append(f'<span class="chip">{e(label)}</span>')

    when = ago(c["closed"] or c["updated"])
    code = f'<span class="code mono">{e(c["code"])}</span>' if c["code"] else ""
    return (
        f'<a class="card" style="border-left-color:{LANE_COLOR[c["lane"]]}" '
        f'href="{e(c["url"])}" target="_blank" rel="noopener">'
        f'<span class="id">{code}<span class="mono">#{c["number"]}</span>'
        f'<span style="margin-left:auto">{e(when)}</span></span>'
        f'<span class="t">{e(c["title"])}</span>'
        f'<span class="chips">{"".join(chips)}</span></a>'
    )


def render(m: dict) -> str:
    by_lane = {k: [c for c in m["cards"] if c["lane"] == k] for k, _, _ in LANES}
    open_count = sum(len(v) for k, v in by_lane.items() if k != "done")
    t = m["tests"]

    stats = [
        ("is-accent", open_count, "open tickets"),
        ("is-good", len(by_lane["done"]), "shipped"),
        ("", len(m["open_prs"]), "open PRs"),
        ("is-warn", len(by_lane["manual"]), "need a click-through"),
        ("", len(m["stacks"]), "live stacks"),
        ("", t["site"] + t["pure"] + t["e2e"], "tests on disk"),
    ]
    stat_html = "".join(
        f'<div class="stat {cls}"><span class="n mono">{n}</span>'
        f'<span class="k">{e(k)}</span></div>'
        for cls, n, k in stats
    )

    lanes = []
    for key, name, note in LANES:
        cards = by_lane[key]
        body = (
            f'<div class="lane-cards">{"".join(render_card(c) for c in cards)}</div>'
            if cards else '<div class="empty">Nothing here.</div>'
        )
        lanes.append(
            f'<section class="lane"><div class="lane-head">'
            f'<div class="row"><span class="dot" style="background:{LANE_COLOR[key]}"></span>'
            f'<span class="lane-name">{e(name)}</span>'
            f'<span class="lane-count mono">{len(cards)}</span></div>'
            f'<div class="lane-note">{e(note)}</div></div>{body}</section>'
        )

    pinned = ""
    if m["pinned"]:
        p = m["pinned"]
        pinned = (
            f'<a class="pinned" href="{e(p["url"])}" target="_blank" rel="noopener">'
            f'<span class="dot" style="background:var(--accent);margin-top:6px"></span><span>'
            f'<span class="t">{e(p["title"])}</span>'
            f'<span class="d">The umbrella spec every ticket below is cut from · '
            f'<span class="mono">#{p["number"]}</span></span></span></a>'
        )

    # Acceptance walkthroughs
    rows = []
    for w in sorted(m["walkthroughs"], key=lambda w: natural(w["file"])):
        pct = round(100 * w["answered"] / w["asked"]) if w["asked"] else 0
        if w["ticket_open"]:
            state = ("warn", "ticket still open")
        elif w["signed_off"]:
            state = ("ok", "signed off")
        elif w["answered"]:
            state = ("warn", "answered")
        else:
            state = ("idle", "unanswered")
        links = " ".join(
            f'<a class="mono code" href="{e(t["url"])}" target="_blank" rel="noopener">'
            f'{e(t["code"])}</a>' for t in w["tickets"]
        ) or '<span class="muted">—</span>'
        rows.append(
            f'<tr><td style="white-space:nowrap">{links}</td>'
            f'<td class="trunc" title="{e(w["title"])}">{e(w["title"])}</td>'
            f'<td class="num mono"><span class="meter"><i style="width:{pct}%"></i></span>'
            f'{w["answered"]}/{w["asked"]}</td>'
            f'<td class="status {state[0]}">{state[1]}</td></tr>'
        )
    walkthroughs = (
        '<div class="scroll"><table><thead><tr><th>Ticket</th><th>Walkthrough</th>'
        '<th class="num">Answered</th><th>State</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table></div>"
    ) if rows else '<div class="empty">No walkthroughs in the repo root.</div>'

    # Preview stacks
    srows = "".join(
        f'<tr><td class="mono code">{e(s["ticket"])}</td>'
        f'<td><a class="mono" href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["url"])}</a></td>'
        f'<td class="muted">{e(s["status"])}</td></tr>'
        for s in m["stacks"]
    )
    stacks = (
        f'<div class="scroll"><table><thead><tr><th>Stack</th><th>URL</th><th>Containers</th>'
        f'</tr></thead><tbody>{srows}</tbody></table></div>'
    ) if srows else '<div class="empty">No preview stacks up. <code class="cmd">./scripts/preview.sh up t8</code></div>'

    # Branches and CI
    brows = []
    for b in m["branches"][:14]:
        r = m["runs"].get(b["name"], {})
        cls = ci_class(r.get("conclusion") or r.get("status"))
        label = r.get("conclusion") or r.get("status") or "no run"
        name = e(b["name"])
        if b["name"] == m["branch"]:
            name = f'{name} <span class="chip">checked out</span>'
        brows.append(
            f'<tr><td class="mono">{name}</td>'
            f'<td class="trunc muted" title="{e(b["subject"])}">{e(b["subject"])}</td>'
            f'<td class="status {cls}">{e(label.replace("_", " "))}</td></tr>'
        )
    branches = (
        '<div class="scroll"><table><thead><tr><th>Branch</th><th>Last commit</th>'
        '<th>CI</th></tr></thead><tbody>' + "".join(brows) + "</tbody></table></div>"
    )

    # Loose PRs
    orphans = ""
    if m["orphan_prs"]:
        orows = "".join(
            f'<tr><td class="mono"><a href="{e(p["url"])}" target="_blank" rel="noopener">'
            f'#{p["number"]}</a></td><td class="trunc">{e(p["title"])}</td>'
            f'<td class="status {ci_class(p["ci"])}">{e((p["ci"] or "no run").replace("_", " "))}</td></tr>'
            for p in m["orphan_prs"]
        )
        orphans = (
            '<section class="panel"><h3>Open PRs with no ticket</h3><div class="scroll"><table>'
            '<thead><tr><th>PR</th><th>Title</th><th>CI</th></tr></thead><tbody>'
            + orows + "</tbody></table></div></section>"
        )

    banner = (
        '<div class="banner">GitHub was unreachable when this ran — the ticket lanes are '
        'empty. Everything below the board is read from the working copy and is still true.</div>'
        if m["offline"] else ""
    )

    live_note = (
        f'This page is a snapshot. The copy that rebuilds itself every five '
        f'minutes is on the box at <a class="mono" href="{e(m["live_url"])}">'
        f'{e(m["live_url"])}</a>.<br>' if m["live_url"] else ""
    )
    e2e_note = (
        f' · <span class="mono">{t["e2e"]}</span> Playwright specs' if t["e2e"] else ""
    )
    dirty = (
        f'{m["dirty"]} uncommitted file{"s" if m["dirty"] != 1 else ""}'
        if m["dirty"] else "clean tree"
    )
    stamp = datetime.fromisoformat(m["generated"]).strftime("%-d %b %Y, %H:%M UTC")

    # charset first: http.server sends text/html with no charset parameter, and
    # a browser left to guess falls back to Latin-1 and mangles every em dash.
    return f"""<meta charset="utf-8">
<title>AuraOS — board</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<header class="top"><div class="wrap">
  <div class="brandline">
    <span class="tally"></span>
    <h1>AuraOS</h1>
    <span class="sub">Deal pipeline, pricing, quotes, jobs, money — one shared system.</span>
    <span class="stamp">Snapshot {e(stamp)}<br>
      <span class="mono">{e(m["branch"])} @ {e(m["head"])}</span> · {e(dirty)}</span>
  </div>
  <div class="stats">{stat_html}</div>
</div></header>

<main class="wrap">
  {banner}
  {pinned}
  <h2>Where every ticket stands</h2>
  <div class="board">{"".join(lanes)}</div>

  <h2>The human half</h2>
  <div class="panels">
    <section class="panel"><h3>Acceptance walkthroughs</h3>{walkthroughs}</section>
    <section class="panel"><h3>Preview stacks up right now</h3>{stacks}</section>
    <section class="panel"><h3>Branches &amp; CI</h3>{branches}</section>
    {orphans}
  </div>

  <footer>
    Automation on this branch: <span class="mono">{t["site"]}</span> Frappe site tests ·
    <span class="mono">{t["pure"]}</span> pure pytest{e2e_note}.<br>
    A ticket lands in <strong>Needs manual test</strong> once its PR is open and CI is green —
    that is the point a walkthrough gets written and a preview stack goes up.<br>
    {live_note}Regenerate by hand with <code class="cmd">./scripts/board.py</code>.
  </footer>
</main>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(REPO / "docs" / "board.html"))
    ap.add_argument("--json", action="store_true", help="print the model instead")
    ap.add_argument(
        "--fetch", action="store_true",
        help="refresh remote-tracking refs first (what the timer uses; "
             "touches no local branch and no working tree)",
    )
    args = ap.parse_args()

    if args.fetch:
        run(["git", "fetch", "--quiet", "origin"])

    model = build_model()
    if args.json:
        print(json.dumps(model, indent=2))
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(model))
    lanes = {k: sum(1 for c in model["cards"] if c["lane"] == k) for k, _, _ in LANES}
    print(f"{out}  " + "  ".join(f"{k}={v}" for k, v in lanes.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
