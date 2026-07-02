from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Any

from agentic.runtime.tick import RuntimeTickResult, RuntimeTickService
from agentic.workflow_kernel.models import utc_now


@dataclass(frozen=True)
class RuntimeDaemonSnapshot:
    running: bool
    tick_count: int = 0
    last_tick_at: str | None = None
    last_error: dict[str, Any] | None = None
    last_result: dict[str, Any] | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "tick_count": self.tick_count,
            "last_tick_at": self.last_tick_at,
            "last_error": self.last_error,
            "last_result": self.last_result,
        }


class RuntimeDaemonLoop:
    def __init__(
        self,
        *,
        tick_service: RuntimeTickService,
        interval_s: float = 10.0,
        tick_timeout_s: float = 120.0,
        wait_for_tasks: bool = False,
    ):
        if interval_s <= 0:
            raise ValueError("daemon interval_s must be positive")
        self.tick_service = tick_service
        self.interval_s = interval_s
        self.tick_timeout_s = tick_timeout_s
        self.wait_for_tasks = wait_for_tasks
        self._stop = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._tick_count = 0
        self._last_tick_at: str | None = None
        self._last_error: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = Thread(target=self._run, name="agentic-runtime-daemon", daemon=True)
            self._thread.start()

    def stop(self, *, timeout_s: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout_s)

    def run_once(self) -> RuntimeTickResult:
        result = self.tick_service.run_once(
            wait=self.wait_for_tasks,
            timeout_s=self.tick_timeout_s,
        )
        self._record_result(result)
        return result

    def snapshot(self) -> RuntimeDaemonSnapshot:
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            return RuntimeDaemonSnapshot(
                running=running,
                tick_count=self._tick_count,
                last_tick_at=self._last_tick_at,
                last_error=self._last_error,
                last_result=self._last_result,
            )

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:
                self._record_error(exc)
            self._stop.wait(self.interval_s)

    def _record_result(self, result: RuntimeTickResult) -> None:
        with self._lock:
            self._tick_count += 1
            self._last_tick_at = utc_now()
            self._last_error = None
            self._last_result = result.to_record()

    def _record_error(self, exc: Exception) -> None:
        with self._lock:
            self._tick_count += 1
            self._last_tick_at = utc_now()
            self._last_error = {"type": exc.__class__.__name__, "message": str(exc)}
