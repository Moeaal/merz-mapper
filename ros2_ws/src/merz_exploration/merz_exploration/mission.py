"""Decide when an exploration run has finished. No ROS imports.

explore_lite does not announce that it has finished, so the rule is based on what can be watched: the run ends when no
frontier has been reported for a while, or the time cap is reached, or the operator asks for it to end.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EndReason(Enum):
    NO_FRONTIERS = 'no frontiers left'
    TIME_CAP = 'time cap reached'
    OPERATOR = 'operator request'


@dataclass
class MissionMonitor:
    max_duration_s: float = 1800.0       # stops a stalled run from draining the battery
    no_frontier_timeout_s: float = 60.0  # long enough to ride out a brief gap in frontiers
    startup_grace_s: float = 30.0        # the map is empty at the start, so "no frontiers" means nothing yet
    _start_s: Optional[float] = None
    _last_frontier_s: Optional[float] = None
    _operator_finished: bool = False

    def start(self, now_s: float) -> None:
        self._start_s = now_s
        self._last_frontier_s = now_s

    def frontiers_seen(self, count: int, now_s: float) -> None:
        if count > 0:
            self._last_frontier_s = now_s

    def request_finish(self) -> None:
        self._operator_finished = True

    def check(self, now_s: float) -> Optional[EndReason]:
        """Return why the mission should end now, or None to continue."""
        if self._operator_finished:
            return EndReason.OPERATOR
        if self._start_s is None:
            return None
        elapsed = now_s - self._start_s
        if elapsed >= self.max_duration_s:
            return EndReason.TIME_CAP
        if elapsed >= self.startup_grace_s and now_s - self._last_frontier_s >= self.no_frontier_timeout_s:
            return EndReason.NO_FRONTIERS
        return None
