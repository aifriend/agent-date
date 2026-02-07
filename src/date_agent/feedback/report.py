"""Report generator for feedback loop runs."""

import json
import os
from collections import Counter
from datetime import datetime

from date_agent.feedback.state import RunState


class ReportGenerator:
    """Generates summary reports from feedback loop runs."""

    def generate(self, state: RunState, output_dir: str) -> str:
        """Generate comprehensive JSON and Markdown reports.

        Returns:
            Path to the JSON report file.
        """
        os.makedirs(output_dir, exist_ok=True)
        suffix = state.run_id[:8]

        total = max(1, state.total_queries_processed)
        report = {
            "run_id": state.run_id,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
            "completion_reason": state.completion_reason,
            "reference_date": state.reference_date,
            "summary": {
                "total_queries": state.total_queries_processed,
                "total_passes": state.total_passes,
                "total_fixes": state.total_fixes_applied,
                "total_skipped": state.total_skipped,
                "pass_rate_pct": round(state.total_passes / total * 100, 2),
                "consecutive_successes": state.consecutive_successes,
                "max_consecutive": state.max_consecutive_achieved,
                "target_reached": state.completion_reason == "target_reached",
            },
            "fixes": state.fixes_applied,
            "failure_breakdown": self._categorize_failures(state),
        }

        # JSON report
        json_path = os.path.join(output_dir, f"feedback_report_{suffix}.json")
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Markdown report
        md_path = os.path.join(output_dir, f"feedback_report_{suffix}.md")
        with open(md_path, "w") as f:
            f.write(self._render_markdown(report))

        return json_path

    def _categorize_failures(self, state: RunState) -> dict:
        """Categorize failures by category and status."""
        category_counts: Counter = Counter()
        status_counts: Counter = Counter()
        for r in state.results:
            status_counts[r.get("status", "unknown")] += 1
            if r.get("status") in ("fixed", "skipped"):
                category_counts[r.get("category", "unknown")] += 1
        return {
            "by_category": dict(category_counts.most_common()),
            "by_status": dict(status_counts.most_common()),
        }

    def _render_markdown(self, report: dict) -> str:
        """Render a human-readable Markdown report."""
        s = report["summary"]
        lines = [
            f"# Feedback Loop Report",
            f"",
            f"- **Run ID**: {report['run_id']}",
            f"- **Started**: {report['started_at']}",
            f"- **Completed**: {report['completed_at']}",
            f"- **Reason**: {report['completion_reason']}",
            f"- **Reference date**: {report['reference_date']}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total queries | {s['total_queries']} |",
            f"| Passes | {s['total_passes']} |",
            f"| Fixes applied | {s['total_fixes']} |",
            f"| Skipped | {s['total_skipped']} |",
            f"| Pass rate | {s['pass_rate_pct']}% |",
            f"| Consecutive successes | {s['consecutive_successes']} |",
            f"| Max consecutive | {s['max_consecutive']} |",
            f"| Target reached | {'Yes' if s['target_reached'] else 'No'} |",
            f"",
        ]

        if report["fixes"]:
            lines.append("## Fixes Applied")
            lines.append("")
            for i, fix in enumerate(report["fixes"], 1):
                lines.append(f"### Fix {i}")
                lines.append(f"- **Query**: {fix.get('query_text', 'N/A')}")
                lines.append(f"- **File**: {fix.get('file_path', 'N/A')}")
                lines.append(f"- **Description**: {fix.get('fix_description', 'N/A')}")
                lines.append("")

        breakdown = report.get("failure_breakdown", {})
        if breakdown.get("by_category"):
            lines.append("## Failure Breakdown by Category")
            lines.append("")
            lines.append("| Category | Count |")
            lines.append("|----------|-------|")
            for cat, cnt in breakdown["by_category"].items():
                lines.append(f"| {cat} | {cnt} |")
            lines.append("")

        return "\n".join(lines)
