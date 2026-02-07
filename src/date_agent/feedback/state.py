"""Persistent state for feedback loop runs."""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional

from date_agent.feedback.models import QueryResult


@dataclass
class RunState:
    """Persistent state for a feedback loop run.

    Enables resuming from where the system left off.
    """

    run_id: str
    started_at: str
    reference_date: str

    # Counters
    total_queries_processed: int = 0
    total_passes: int = 0
    total_fixes_applied: int = 0
    total_skipped: int = 0
    consecutive_successes: int = 0
    max_consecutive_achieved: int = 0

    # Per-query results (summary only)
    results: List[dict] = field(default_factory=list)

    # Fixes applied (audit trail)
    fixes_applied: List[dict] = field(default_factory=list)

    # Completion
    completed: bool = False
    completed_at: Optional[str] = None
    completion_reason: Optional[str] = None

    def save(self, path: str) -> None:
        """Save state to disk."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> "RunState":
        """Load state from disk."""
        with open(path, "r") as f:
            data = json.load(f)
        known_fields = cls.__dataclass_fields__
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def record_pass(self, qr: QueryResult) -> None:
        """Record a passing query."""
        self.total_queries_processed += 1
        self.total_passes += 1
        self.consecutive_successes += 1
        self.max_consecutive_achieved = max(
            self.max_consecutive_achieved, self.consecutive_successes
        )
        self.results.append({
            "query_id": qr.query.query_id,
            "query_text": qr.query.query_text[:80],
            "category": qr.query.category.value,
            "status": "passed",
            "consecutive": self.consecutive_successes,
        })

    def record_fix(self, qr: QueryResult) -> None:
        """Record a fixed query (resets counter)."""
        self.total_queries_processed += 1
        self.total_fixes_applied += 1
        self.consecutive_successes = 0  # RESET
        self.results.append({
            "query_id": qr.query.query_id,
            "query_text": qr.query.query_text[:80],
            "category": qr.query.category.value,
            "status": "fixed",
        })
        # Record fix details
        if qr.fix_attempts:
            last_fix = qr.fix_attempts[-1]
            self.fixes_applied.append({
                "query_id": qr.query.query_id,
                "query_text": qr.query.query_text[:80],
                "file_path": last_fix.file_path,
                "fix_description": last_fix.fix_description,
                "attempt_number": last_fix.attempt_number,
            })

    def record_skip(self, qr: QueryResult) -> None:
        """Record a skipped query (could not fix). Counter unchanged."""
        self.total_queries_processed += 1
        self.total_skipped += 1
        # Don't reset counter - no code changed
        self.results.append({
            "query_id": qr.query.query_id,
            "query_text": qr.query.query_text[:80],
            "category": qr.query.category.value,
            "status": "skipped",
            "reason": qr.validation.result.value if qr.validation else "unknown",
        })
