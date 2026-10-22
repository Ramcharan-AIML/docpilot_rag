"""Milliseconds per stage (embed, search, rerank, ...), reported as p50 / p95 (step 3.5).

Use:
    times = StageTimes()
    with times.measure("rerank"):
        hits = rerank(question, hits, keep=10)
    times.summary()  # {"rerank": {"n": 41, "p50": ..., "p95": ...}}
"""

import time
from collections import defaultdict
from contextlib import contextmanager

from evals.metrics import percentile


class StageTimes:
    """Collects one time per question for each stage name."""

    def __init__(self) -> None:
        self.times: dict[str, list[float]] = defaultdict(list)

    @contextmanager
    def measure(self, stage: str):
        """Time the code inside the `with` block and save it under `stage`."""
        start = time.perf_counter()
        try:
            yield
        finally:
            self.times[stage].append(round((time.perf_counter() - start) * 1000, 1))

    def summary(self) -> dict[str, dict]:
        """p50 and p95 per stage, in the order the stages were first measured."""
        return {
            stage: {"n": len(values), "p50": percentile(values, 50), "p95": percentile(values, 95)}
            for stage, values in self.times.items()
        }
