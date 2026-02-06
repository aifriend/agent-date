"""Audit trail functionality for compliance tracking."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone as tz
from pathlib import Path
from typing import Any, Optional
import uuid


@dataclass
class AuditEntry:
    """A single audit trail entry for compliance.

    Records all details of a date calculation for traceability.

    Attributes:
        execution_id: Unique identifier for this execution.
        timestamp: When this entry was created.
        query: The original user query.
        tool_name: Name of the tool that was executed.
        input_params: Parameters passed to the tool.
        output_result: Result returned by the tool.
        reference_date_used: The reference date anchor (ISO format).
        calendar_system: Calendar system used for calculation.
        timezone: Timezone used for calculation.
        computation_steps: Step-by-step trace of the calculation.
        duration_ms: Execution duration in milliseconds.
        success: Whether the execution succeeded.
        error_message: Error message if execution failed.
    """

    execution_id: str
    timestamp: datetime
    query: str
    tool_name: str
    input_params: dict[str, Any]
    output_result: dict[str, Any]
    reference_date_used: str
    calendar_system: str
    timezone: str
    computation_steps: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert datetime to ISO format string
        result["timestamp"] = self.timestamp.isoformat()
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass
class AuditSession:
    """A complete audit session containing multiple entries.

    Groups all audit entries for a single user query.

    Attributes:
        session_id: Unique identifier for this session.
        created_at: When the session was created.
        query: The original user query.
        entries: List of audit entries.
        total_duration_ms: Total execution time.
        final_result: The final result returned to the user.
    """

    session_id: str
    created_at: datetime
    query: str
    entries: list[AuditEntry] = field(default_factory=list)
    total_duration_ms: float = 0.0
    final_result: Optional[dict[str, Any]] = None

    def add_entry(self, entry: AuditEntry) -> None:
        """Add an audit entry to this session."""
        self.entries.append(entry)
        self.total_duration_ms += entry.duration_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "query": self.query,
            "entries": [e.to_dict() for e in self.entries],
            "total_duration_ms": self.total_duration_ms,
            "final_result": self.final_result,
        }


class AuditManager:
    """Manages audit trail recording and retrieval.

    Provides methods to log executions, retrieve entries,
    and persist audit data for compliance.
    """

    def __init__(
        self,
        enabled: bool = True,
        log_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize the audit manager.

        Args:
            enabled: Whether audit logging is enabled.
            log_path: Path to write audit logs (optional).
            logger: Logger instance (optional).
        """
        self.enabled = enabled
        self.log_path = Path(log_path) if log_path else None
        self.logger = logger or logging.getLogger("AuditManager")

        # In-memory storage for sessions
        self._sessions: dict[str, AuditSession] = {}

        # Ensure log directory exists
        if self.log_path:
            self.log_path.mkdir(parents=True, exist_ok=True)

    def create_session(self, query: str) -> str:
        """Create a new audit session.

        Args:
            query: The original user query.

        Returns:
            The session ID.
        """
        if not self.enabled:
            return ""

        session_id = str(uuid.uuid4())
        session = AuditSession(
            session_id=session_id,
            created_at=datetime.now(tz.utc),
            query=query,
        )
        self._sessions[session_id] = session
        self.logger.debug(f"Created audit session: {session_id}")
        return session_id

    async def log_tool_execution(
        self,
        session_id: str,
        execution_id: str,
        tool_name: str,
        input_params: dict[str, Any],
        output_result: dict[str, Any],
        reference_date: datetime,
        calendar_system: str,
        timezone: str,
        computation_steps: list[str],
        duration_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Log a tool execution to the audit trail.

        Args:
            session_id: The session this execution belongs to.
            execution_id: Unique ID for this execution.
            tool_name: Name of the executed tool.
            input_params: Parameters passed to the tool.
            output_result: Result from the tool.
            reference_date: The reference date used.
            calendar_system: Calendar system used.
            timezone: Timezone used.
            computation_steps: Step-by-step trace.
            duration_ms: Execution duration.
            success: Whether execution succeeded.
            error_message: Error message if failed.
        """
        if not self.enabled:
            return

        session = self._sessions.get(session_id)
        if not session:
            self.logger.warning(f"Session not found for logging: {session_id}")
            return

        entry = AuditEntry(
            execution_id=execution_id,
            timestamp=datetime.now(tz.utc),
            query=session.query,
            tool_name=tool_name,
            input_params=input_params,
            output_result=output_result,
            reference_date_used=reference_date.isoformat(),
            calendar_system=calendar_system,
            timezone=timezone,
            computation_steps=computation_steps,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
        )
        session.add_entry(entry)
        self.logger.debug(f"Logged tool execution: {tool_name} ({duration_ms}ms)")

    async def finalize_session(
        self,
        session_id: str,
        final_result: dict[str, Any],
    ) -> Optional[AuditSession]:
        """Finalize an audit session and optionally persist it.

        Args:
            session_id: The session to finalize.
            final_result: The final result returned to the user.

        Returns:
            The finalized audit session, or None if session not found.
        """
        if not self.enabled:
            return None

        session = self._sessions.get(session_id)
        if not session:
            self.logger.warning(f"Session not found for finalization: {session_id}")
            return None

        session.final_result = final_result

        # Persist to file if log_path is configured
        if self.log_path:
            await self._persist_session(session)

        self.logger.info(
            f"Finalized audit session: {session_id} "
            f"({len(session.entries)} entries, {session.total_duration_ms}ms total)"
        )
        return session

    async def _persist_session(self, session: AuditSession) -> None:
        """Persist a session to the log file.

        Args:
            session: The session to persist.
        """
        if not self.log_path:
            return

        # Use date-based file naming for organization
        date_str = session.created_at.strftime("%Y-%m-%d")
        log_file = self.log_path / f"audit_{date_str}.jsonl"

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(session.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to persist audit session: {e}")

    async def get_session(self, session_id: str) -> Optional[AuditSession]:
        """Retrieve an audit session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The audit session, or None if not found.
        """
        return self._sessions.get(session_id)

    async def get_entry(self, execution_id: str) -> Optional[AuditEntry]:
        """Retrieve an audit entry by execution ID.

        Args:
            execution_id: The execution ID.

        Returns:
            The audit entry, or None if not found.
        """
        for session in self._sessions.values():
            for entry in session.entries:
                if entry.execution_id == execution_id:
                    return entry
        return None

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Remove old sessions from memory.

        Args:
            max_age_hours: Maximum age of sessions to keep.

        Returns:
            Number of sessions removed.
        """
        cutoff = datetime.now(tz.utc).timestamp() - (max_age_hours * 3600)
        old_sessions = [
            sid
            for sid, session in self._sessions.items()
            if session.created_at.timestamp() < cutoff
        ]
        for sid in old_sessions:
            del self._sessions[sid]

        if old_sessions:
            self.logger.info(f"Cleaned up {len(old_sessions)} old audit sessions")
        return len(old_sessions)
