# Simple scheduler and priority queue for radio sync operations
from __future__ import annotations
import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

@dataclass(order=True)
class PrioritizedItem:
    priority: int
    item: Any=field(compare=False)
    attempts: int=field(default=0, compare=False)
    next_attempt: float=field(default_factory=lambda: time.time(), compare=False)

class PrioritySyncQueue:
    """In-memory priority queue with retry/backoff metadata."""
    def __init__(self):
        self._heap: List[PrioritizedItem] = []

    def push(self, item: Any, priority: int = 10) -> None:
        heapq.heappush(self._heap, PrioritizedItem(priority, item))

    def pop(self) -> Optional[PrioritizedItem]:
        if not self._heap:
            return None
        top = self._heap[0]
        if top.next_attempt <= time.time():
            return heapq.heappop(self._heap)
        return None

    def __len__(self) -> int:
        return len(self._heap)

class LinkScheduler:
    """Schedule periodic sync jobs respecting duty-cycle limits."""

    def __init__(self, send_fn: Callable[[bytes], None], window: float = 60.0,
                 busy_check: Optional[Callable[[], bool]] = None):
        self.send_fn = send_fn
        self.window = window
        self.busy_check = busy_check
        self.queue = PrioritySyncQueue()
        self._last_tx = 0.0

    def queue_packet(self, packet: bytes, priority: int = 10) -> None:
        self.queue.push(packet, priority)

    def run_once(self) -> None:
        if not len(self.queue):
            return
        item = self.queue.pop()
        if not item:
            return
        if self.busy_check and self.busy_check():
            item.next_attempt = time.time() + self.window
            self.queue.push(item.item, item.priority)
            return
        if time.time() - self._last_tx < self.window:
            # not within allowed window yet
            item.next_attempt = time.time() + self.window
            self.queue.push(item.item, item.priority)
            return
        try:
            self.send_fn(item.item)
            self._last_tx = time.time()
        except Exception:
            item.attempts += 1
            # simple exponential backoff
            item.next_attempt = time.time() + min(60 * (2 ** item.attempts), 3600)
            self.queue.push(item.item, item.priority)
