from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def pick_rotating_routes(
    *,
    all_routes: list[tuple[str, str]],
    budget_requests: int,
    state_file_path: str,
    trip_type: int,
    return_days_min: int,
    return_days_max: int,
    return_days_step: int,
    requests_per_route: int,
) -> list[tuple[str, str]]:
    if not all_routes:
        return []

    state_path = Path(state_file_path)
    state = _read_state(state_path)
    today = date.today().isoformat()
    if state.get("last_date") != today:
        state["last_date"] = today

    route_count = len(all_routes)
    last_index = _safe_int(state.get("last_route_index"), -1)
    start_index = (last_index + 1) % route_count

    if requests_per_route <= 0:
        if trip_type == 1:
            return_count = ((return_days_max - return_days_min) // return_days_step) + 1
            requests_per_route = max(1, return_count)
        else:
            requests_per_route = 1

    max_routes_today = max(1, budget_requests // requests_per_route)
    selected_count = min(route_count, max_routes_today)

    selected: list[tuple[str, str]] = []
    idx = start_index
    for _ in range(selected_count):
        selected.append(all_routes[idx])
        idx = (idx + 1) % route_count

    state["last_route_index"] = (start_index + selected_count - 1) % route_count
    _write_state(state_path, state)
    return selected

