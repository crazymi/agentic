from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from agentic.runtime.worker import TaskExecutor, TaskWorker
from agentic.tasks.store import TaskStore


class TaskPool:
    def __init__(
        self,
        *,
        store: TaskStore,
        executor: TaskExecutor,
        max_workers: int = 1,
        heartbeat_interval_s: float = 15.0,
    ):
        self.store = store
        self.worker = TaskWorker(
            store,
            executor,
            heartbeat_interval_s=heartbeat_interval_s,
        )
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = Lock()
        self._futures: set[Future] = set()
        self._closed = False

    def kick(self) -> int:
        submitted = 0
        new_futures: list[Future] = []
        with self._lock:
            self._prune_locked()
            while not self._closed and len(self._futures) < self.max_workers:
                task = self.store.claim_next()
                if task is None:
                    break
                future = self._executor.submit(self.worker.run_claimed_task, task)
                self._futures.add(future)
                new_futures.append(future)
                submitted += 1
        for future in new_futures:
            future.add_done_callback(lambda _future: self.kick())
        return submitted

    def running_count(self) -> int:
        with self._lock:
            self._prune_locked()
            return len(self._futures)

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _prune_locked(self) -> None:
        self._futures = {future for future in self._futures if not future.done()}
