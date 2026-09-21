#!/usr/bin/env python3
"""Create at most the planned number of activity commits for the local day.

The target is deliberately deterministic for a given date. That makes retries
safe: a delayed or repeated Actions run cannot change today's target.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import update_github_stats


ROOT = Path(__file__).resolve().parents[1]
HEARTBEAT_PATH = ROOT / ".github" / "activity-heartbeat.txt"
MARKER = "chore: daily activity heartbeat"
TARGETS = (4, 6, 8)


def get_timezone():
    timezone_name = os.environ.get("ACTIVITY_TIMEZONE", "Asia/Shanghai")
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        # Asia/Shanghai has no daylight-saving transition. The fixed-offset
        # fallback keeps local Windows tests working without a tzdata package.
        if timezone_name == "Asia/Shanghai":
            return timezone(timedelta(hours=8), name="Asia/Shanghai")
        return timezone.utc


def get_now() -> datetime:
    return datetime.now(get_timezone())


def target_for(day: str) -> int:
    digest = hashlib.sha256(day.encode("utf-8")).digest()
    return TARGETS[digest[0] % len(TARGETS)]


def count_today_commits(start: datetime, end: datetime) -> int:
    result = subprocess.run(
        [
            "git",
            "log",
            "--all",
            f"--since={start.strftime('%Y-%m-%dT%H:%M:%S%z')}",
            f"--until={end.strftime('%Y-%m-%dT%H:%M:%S%z')}",
            "--format=%s",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return sum(line.startswith(MARKER) for line in result.stdout.splitlines())


def write_heartbeat(now: datetime, target: int, completed: int) -> None:
    HEARTBEAT_PATH.write_text(
        "\n".join(
            [
                f"date={now.date().isoformat()}",
                f"target={target}",
                f"completed={completed}",
                f"updated_at={now.isoformat(timespec='seconds')}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    now = get_now()
    start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
    target = target_for(now.date().isoformat())
    completed = count_today_commits(start, now)

    print(f"Today's deterministic activity target: {target}")
    print(f"Heartbeat commits already completed: {completed}")

    if completed >= target:
        print("Today's target is complete; leaving the working tree unchanged.")
        return

    # Keep the existing README statistics behavior, but only run it when this
    # run is going to make a heartbeat commit. This prevents a stats-only
    # change from adding an unplanned contribution after today's target.
    update_github_stats.main()
    write_heartbeat(now, target, completed + 1)
    print(f"Prepared heartbeat commit {completed + 1}/{target}.")


if __name__ == "__main__":
    main()
