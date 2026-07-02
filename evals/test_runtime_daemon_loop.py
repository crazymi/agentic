from __future__ import annotations

import time
import unittest

from agentic.runtime.daemon_loop import RuntimeDaemonLoop
from agentic.runtime.tick import RuntimeTickResult


class CountingTickService:
    def __init__(self):
        self.calls = 0

    def run_once(self, *, wait: bool = True, timeout_s: float = 120.0) -> RuntimeTickResult:
        self.calls += 1
        return RuntimeTickResult(tasks_submitted=self.calls)


class RuntimeDaemonLoopTests(unittest.TestCase):
    def test_daemon_loop_runs_repeated_ticks(self) -> None:
        tick = CountingTickService()
        daemon = RuntimeDaemonLoop(
            tick_service=tick,
            interval_s=0.05,
            tick_timeout_s=1,
            wait_for_tasks=False,
        )

        daemon.start()
        time.sleep(0.13)
        daemon.stop()

        snapshot = daemon.snapshot()
        self.assertGreaterEqual(tick.calls, 2)
        self.assertGreaterEqual(snapshot.tick_count, 2)
        self.assertFalse(snapshot.running)
        self.assertIsNone(snapshot.last_error)

    def test_run_once_records_snapshot(self) -> None:
        tick = CountingTickService()
        daemon = RuntimeDaemonLoop(tick_service=tick, interval_s=1)

        result = daemon.run_once()

        self.assertEqual(result.tasks_submitted, 1)
        self.assertEqual(daemon.snapshot().tick_count, 1)


if __name__ == "__main__":
    unittest.main()
